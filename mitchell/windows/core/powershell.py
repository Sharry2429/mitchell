import base64
import ctypes
import locale
import logging
import os
import subprocess
import winreg

from mitchell.core.audit import check_destructive, log_action
from mitchell.windows.config import get_config
from mitchell.windows.types import CommandResult

logger = logging.getLogger(__name__)


def is_elevated() -> bool:
    """Check if current process has admin rights."""
    try:
        return ctypes.windll.shell32.IsUserAnAdmin() != 0
    except Exception:
        return False


def get_powershell_path() -> str:
    """Find pwsh or powershell.exe."""
    try:
        # Check for PowerShell Core (pwsh) first
        result = subprocess.run(
            ["where", "pwsh"], capture_output=True, text=True, check=False
        )
        if result.returncode == 0 and result.stdout.strip():
            return result.stdout.strip().split("\n")[0].strip()
    except Exception:
        pass

    # Fallback to Windows PowerShell
    return "powershell.exe"


def _get_registry_env(key, subkey: str) -> dict[str, str]:
    env = {}
    try:
        with winreg.OpenKey(key, subkey) as reg_key:
            i = 0
            while True:
                try:
                    name, value, _ = winreg.EnumValue(reg_key, i)
                    env[name] = str(value)
                    i += 1
                except OSError:
                    break
    except OSError as e:
        logger.warning(f"Failed to read registry key {subkey}: {e}")
    return env


def _get_computer_name() -> str:
    """Get COMPUTERNAME via Win32 API."""
    size = ctypes.c_uint32(256)
    buf = ctypes.create_unicode_buffer(size.value)
    if ctypes.windll.kernel32.GetComputerNameW(buf, ctypes.byref(size)):
        return buf.value
    return os.environ.get("COMPUTERNAME", "UNKNOWN")


def _get_user_name() -> str:
    """Get USERNAME via Win32 API."""
    size = ctypes.c_uint32(256)
    buf = ctypes.create_unicode_buffer(size.value)
    if ctypes.windll.advapi32.GetUserNameW(buf, ctypes.byref(size)):
        return buf.value
    return os.environ.get("USERNAME", "UNKNOWN")


def _prepare_env() -> dict[str, str]:
    """Reconstruct full environment."""
    # Start with a clean copy of the current environment to get things like SystemRoot
    env = os.environ.copy()

    # Read system and user env vars from registry
    sys_env = _get_registry_env(
        winreg.HKEY_LOCAL_MACHINE,
        r"SYSTEM\CurrentControlSet\Control\Session Manager\Environment",
    )
    user_env = _get_registry_env(winreg.HKEY_CURRENT_USER, r"Environment")

    # Apply registry environment variables
    env.update(sys_env)
    env.update(user_env)

    # Reconstruct PATH by merging system + user paths
    sys_path = sys_env.get("PATH", "")
    user_path = user_env.get("PATH", "")

    if sys_path and user_path:
        env["PATH"] = f"{sys_path};{user_path}"
    elif sys_path:
        env["PATH"] = sys_path
    elif user_path:
        env["PATH"] = user_path

    # Get COMPUTERNAME and USERNAME via Win32 API
    env["COMPUTERNAME"] = _get_computer_name()
    env["USERNAME"] = _get_user_name()

    return env


def _run_with_timeout(
    args: list[str],
    timeout: int | None,
    env: dict[str, str],
    requested_encoding: str | None = None,
) -> CommandResult:
    try:
        process = subprocess.Popen(
            args,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env=env,
            creationflags=subprocess.CREATE_NO_WINDOW,
        )

        try:
            stdout_bytes, stderr_bytes = process.communicate(timeout=timeout)
        except subprocess.TimeoutExpired:
            process.kill()
            stdout_bytes, stderr_bytes = process.communicate()

            encoding = requested_encoding or locale.getpreferredencoding() or "utf-8"
            return CommandResult(
                stdout=stdout_bytes.decode(encoding, errors="replace"),
                stderr=f"Command timed out after {timeout} seconds\n"
                + stderr_bytes.decode(encoding, errors="replace"),
                exit_code=-1,
            )

        encoding = requested_encoding or locale.getpreferredencoding() or "utf-8"
        return CommandResult(
            stdout=stdout_bytes.decode(encoding, errors="replace"),
            stderr=stderr_bytes.decode(encoding, errors="replace"),
            exit_code=process.returncode,
        )
    except Exception as e:
        return CommandResult(
            stdout="", stderr=f"Failed to execute command: {e}", exit_code=-2
        )


def execute(
    command: str,
    timeout: int | None = None,
    as_admin: bool = False,
    encoding: str | None = None,
    confirm: bool = False,
) -> CommandResult:
    check_destructive("shell.execute", confirm)
    log_action("windows.powershell", "execute", {"command": command}, {})
    config = get_config()
    # Use provided timeout or fallback to config, if it is None
    actual_timeout = (
        timeout if timeout is not None else getattr(config, "default_timeout", 60)
    )

    if as_admin and not is_elevated():
        return CommandResult(
            stdout="",
            stderr="Administrator privileges required to execute this command.",
            exit_code=-3,
        )

    ps_path = get_powershell_path()

    # Base64-encode commands for -EncodedCommand to avoid quoting issues
    encoded_command = base64.b64encode(command.encode("utf-16le")).decode("ascii")

    args = [
        ps_path,
        "-NoProfile",
        "-NonInteractive",
        "-ExecutionPolicy",
        "Bypass",
        "-EncodedCommand",
        encoded_command,
    ]
    env = _prepare_env()

    return _run_with_timeout(args, actual_timeout, env, requested_encoding=encoding)


def execute_script(
    script_path: str, args: list[str] | None = None, timeout: int | None = None, confirm: bool = False
) -> CommandResult:
    check_destructive("shell.execute", confirm)
    log_action("windows.powershell", "execute_script", {"script_path": script_path, "args": args}, {})
    config = get_config()
    actual_timeout = (
        timeout if timeout is not None else getattr(config, "default_timeout", 60)
    )

    ps_path = get_powershell_path()
    cmd_args = [
        ps_path,
        "-NoProfile",
        "-NonInteractive",
        "-ExecutionPolicy",
        "Bypass",
        "-File",
        script_path,
    ]

    if args:
        cmd_args.extend(args)

    env = _prepare_env()

    return _run_with_timeout(cmd_args, actual_timeout, env)

import subprocess

from mitchell.android import adb
from mitchell.android.base import confirm_destructive
from mitchell.android.connection import get_adb_prefix
from mitchell.core.audit import log_action
from mitchell.core.errors import PermissionDenied, SystemMCPError
from mitchell.core.result import MCPResult

"\nAndroid power management via ADB.\n"


def reboot(confirm: bool = False):
    """Reboots the device."""
    try:
        confirm_destructive("reboot", confirm)
        log_action("power", "reboot", {}, {})
        result = adb.run(["reboot"])
        if (
            hasattr(result, "stderr")
            and result.stderr
            and ("Permission denied" in result.stderr)
        ):
            return MCPResult.fail(result.stderr)
        return MCPResult.success(True)
    except Exception as e:
        return MCPResult.fail(str(e))


def shutdown(confirm: bool = False):
    """Shuts down the device."""
    try:
        confirm_destructive("shutdown", confirm)
        log_action("power", "shutdown", {}, {})
        result = adb.shell(["reboot", "-p"])
        if (
            hasattr(result, "stderr")
            and result.stderr
            and ("Permission denied" in result.stderr)
        ):
            return MCPResult.fail(result.stderr)
        return MCPResult.success(True)
    except Exception as e:
        return MCPResult.fail(str(e))


def screen_on():
    """Turns the screen on."""
    try:
        log_action("power", "screen_on", {}, {})
        adb.shell(["input", "keyevent", "KEYCODE_WAKEUP"])
        return MCPResult.success(True)
    except Exception as e:
        return MCPResult.fail(str(e))


def screen_off():
    """Turns the screen off."""
    try:
        log_action("power", "screen_off", {}, {})
        adb.shell(["input", "keyevent", "KEYCODE_SLEEP"])
        return MCPResult.success(True)
    except Exception as e:
        return MCPResult.fail(str(e))


def wake():
    """Alias for screen_on."""
    return screen_on()


def stay_awake(enable: bool):
    """Keeps the screen on while plugged in."""
    try:
        log_action("power", "stay_awake", {"enable": enable}, {})
        state = "true" if enable else "false"
        result = adb.shell(["svc", "power", "stayon", state])
        if (
            hasattr(result, "stderr")
            and result.stderr
            and ("Permission denied" in result.stderr or "Killed" in result.stderr)
        ):
            return MCPResult.fail("Permission denied or svc command failed")
        return MCPResult.success(True)
    except Exception as e:
        return MCPResult.fail(str(e))


"\nAndroid process management via ADB.\n"


def list():
    """Lists running processes."""
    try:
        log_action("process", "list", {}, {})
        result = adb.shell(["ps", "-A"])
        if (
            hasattr(result, "stderr")
            and result.stderr
            and ("Permission denied" in result.stderr)
        ):
            return MCPResult.fail(result.stderr)
        data = result.stdout if hasattr(result, "stdout") else result
        return MCPResult.success(data)
    except Exception as e:
        return MCPResult.fail(str(e))


def top(n: int = 10):
    """Shows top processes by CPU usage."""
    try:
        log_action("process", "top", {"n": n}, {})
        result = adb.shell(["top", "-n", "1", "-m", str(n)])
        data = result.stdout if hasattr(result, "stdout") else result
        return MCPResult.success(data)
    except Exception as e:
        return MCPResult.fail(str(e))


def kill(process_name: str, confirm: bool = False):
    """Kills a process by name."""
    try:
        confirm_destructive("kill", confirm)
        log_action("process", "kill", {"process_name": process_name}, {})
        result = adb.shell(["pkill", process_name])
        if (
            hasattr(result, "stderr")
            and result.stderr
            and (
                "Permission denied" in result.stderr
                or "Operation not permitted" in result.stderr
            )
        ):
            return MCPResult.fail(result.stderr)
        data = result.stdout if hasattr(result, "stdout") else result
        return MCPResult.success(data)
    except Exception as e:
        return MCPResult.fail(str(e))


def kill_pid(pid: int, confirm: bool = False):
    """Kills a process by PID."""
    try:
        confirm_destructive("kill_pid", confirm)
        log_action("process", "kill_pid", {"pid": pid}, {})
        result = adb.shell(["kill", "-9", str(pid)])
        if (
            hasattr(result, "stderr")
            and result.stderr
            and (
                "Permission denied" in result.stderr
                or "Operation not permitted" in result.stderr
            )
        ):
            return MCPResult.fail(result.stderr)
        data = result.stdout if hasattr(result, "stdout") else result
        return MCPResult.success(data)
    except Exception as e:
        return MCPResult.fail(str(e))


def run(command: str) -> MCPResult:
    log_action("shell", "run", {"command": command}, {})
    try:
        result = adb.shell([command])
        return MCPResult.success(result)
    except PermissionDenied as e:
        return MCPResult.fail(str(e))
    except SystemMCPError as e:
        return MCPResult.fail(str(e))
    except Exception as e:
        return MCPResult.fail(str(e))


def run_background(command: str) -> MCPResult:
    log_action("shell", "run_background", {"command": command}, {})
    try:
        cmd = get_adb_prefix() + ["shell", command]
        subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return MCPResult.success(None)
    except Exception as e:
        return MCPResult.fail(str(e))


def pipe(cmd1: str, cmd2: str) -> MCPResult:
    log_action("shell", "pipe", {"cmd1": cmd1, "cmd2": cmd2}, {})
    full_cmd = f"{cmd1} | {cmd2}"
    return run(full_cmd)


"\nAndroid system information via ADB.\n"


def cpu():
    """Returns CPU information from /proc/cpuinfo."""
    try:
        log_action("sysinfo", "cpu", {}, {})
        result = adb.shell(["cat", "/proc/cpuinfo"])
        data = result.stdout if hasattr(result, "stdout") else result
        return MCPResult.success(data)
    except Exception as e:
        return MCPResult.fail(str(e))


def memory():
    """Returns memory information from /proc/meminfo."""
    try:
        log_action("sysinfo", "memory", {}, {})
        result = adb.shell(["cat", "/proc/meminfo"])
        data = result.stdout if hasattr(result, "stdout") else result
        return MCPResult.success(data)
    except Exception as e:
        return MCPResult.fail(str(e))


def battery():
    """Returns battery status from dumpsys."""
    try:
        log_action("sysinfo", "battery", {}, {})
        result = adb.shell(["dumpsys", "battery"])
        data = result.stdout if hasattr(result, "stdout") else result
        return MCPResult.success(data)
    except Exception as e:
        return MCPResult.fail(str(e))


def os_version():
    """Returns the Android OS version string."""
    try:
        log_action("sysinfo", "os_version", {}, {})
        result = adb.shell(["getprop", "ro.build.version.release"])
        data = result.stdout if hasattr(result, "stdout") else result
        return MCPResult.success(data.strip() if isinstance(data, str) else data)
    except Exception as e:
        return MCPResult.fail(str(e))


def logcat(lines: int = 100):
    """Returns the last N lines of logcat."""
    try:
        log_action("sysinfo", "logcat", {"lines": lines}, {})
        result = adb.run(["logcat", "-d", "-t", str(lines)])
        if (
            hasattr(result, "stderr")
            and result.stderr
            and ("Permission denied" in result.stderr)
        ):
            return MCPResult.fail(result.stderr)
        data = result.stdout if hasattr(result, "stdout") else result
        return MCPResult.success(data)
    except Exception as e:
        return MCPResult.fail(str(e))


def display():
    """Returns display/window information."""
    try:
        log_action("sysinfo", "display", {}, {})
        result = adb.shell(["dumpsys", "window", "displays"])
        data = result.stdout if hasattr(result, "stdout") else result
        return MCPResult.success(data)
    except Exception as e:
        return MCPResult.fail(str(e))


def device_model():
    """Returns the device model name."""
    try:
        log_action("sysinfo", "device_model", {}, {})
        result = adb.shell(["getprop", "ro.product.model"])
        data = result.stdout if hasattr(result, "stdout") else result
        return MCPResult.success(data.strip() if isinstance(data, str) else data)
    except Exception as e:
        return MCPResult.fail(str(e))


def storage():
    """Returns disk usage information."""
    try:
        log_action("sysinfo", "storage", {}, {})
        result = adb.shell(["df", "-h"])
        data = result.stdout if hasattr(result, "stdout") else result
        return MCPResult.success(data)
    except Exception as e:
        return MCPResult.fail(str(e))


"\nAndroid settings management.\nReads settings via ADB.\n"


def get_prop(name: str) -> MCPResult:
    """Gets an Android system property via adb shell getprop."""
    log_action("settings", "get_prop", {"name": name}, {})
    try:
        result = adb.shell(["getprop", name])
        return MCPResult.success(result.strip() if result else "")
    except Exception as e:
        return MCPResult.fail(str(e))


def set_prop(name: str, value: str) -> MCPResult:
    """Sets an Android system property. Requires root on most properties."""
    log_action("settings", "set_prop", {"name": name, "value": value}, {})
    try:
        adb.shell(["setprop", name, value])
        return MCPResult.success(None)
    except Exception as e:
        return MCPResult.fail(str(e))


def get_setting(namespace: str, key: str) -> MCPResult:
    """Gets an Android setting from a namespace (system, secure, global) via ADB."""
    log_action("settings", "get_setting", {"namespace": namespace, "key": key}, {})
    try:
        result = adb.shell(["settings", "get", namespace, key])
        return MCPResult.success(result.strip() if result else "")
    except Exception as e:
        return MCPResult.fail(str(e))


def set_setting(namespace: str, key: str, value: str) -> MCPResult:
    """Sets an Android setting via ADB."""
    log_action(
        "settings",
        "set_setting",
        {"namespace": namespace, "key": key, "value": value},
        {},
    )
    try:
        adb.shell(["settings", "put", namespace, key, value])
        return MCPResult.success(None)
    except Exception as e:
        return MCPResult.fail(str(e))


"\nAndroid permission management via ADB.\n"


def list_granted(package_name: str) -> MCPResult:
    """Lists permissions currently granted to the specified package."""
    log_action("permissions", "list_granted", {"package": package_name}, {})
    try:
        result = adb.shell(["dumpsys", "package", package_name])
        granted = []
        in_perms = False
        for line in result.stdout.splitlines():
            stripped = line.strip()
            if "granted permissions:" in stripped.lower():
                in_perms = True
                continue
            if in_perms:
                if stripped.startswith("android.permission.") or stripped.startswith(
                    "com."
                ):
                    granted.append(stripped.rstrip(":").strip())
                elif stripped == "" or ":" in stripped:
                    break
        return MCPResult.success(granted)
    except SystemMCPError as e:
        return MCPResult.fail(str(e))


def list_declared(package_name: str) -> MCPResult:
    """Lists permissions declared in the manifest of the specified package."""
    log_action("permissions", "list_declared", {"package": package_name}, {})
    try:
        result = adb.shell(["dumpsys", "package", package_name])
        declared = []
        in_requested = False
        for line in result.stdout.splitlines():
            stripped = line.strip()
            if "requested permissions:" in stripped.lower():
                in_requested = True
                continue
            if in_requested:
                if stripped.startswith("android.permission.") or stripped.startswith(
                    "com."
                ):
                    declared.append(stripped)
                elif stripped == "" or ":" in stripped:
                    break
        return MCPResult.success(declared)
    except SystemMCPError as e:
        return MCPResult.fail(str(e))


def grant(package_name: str, permission: str) -> MCPResult:
    """Grants a specific permission to the package via ADB."""
    log_action(
        "permissions", "grant", {"package": package_name, "permission": permission}, {}
    )
    try:
        result = adb.shell(["pm", "grant", package_name, permission])
        if result.returncode != 0:
            return MCPResult.fail(
                f"Failed to grant {permission}: {result.stderr.strip()}"
            )
        return MCPResult.success(None)
    except SystemMCPError as e:
        return MCPResult.fail(str(e))


def revoke(package_name: str, permission: str) -> MCPResult:
    """Revokes a specific permission from the package via ADB."""
    log_action(
        "permissions", "revoke", {"package": package_name, "permission": permission}, {}
    )
    try:
        result = adb.shell(["pm", "revoke", package_name, permission])
        if result.returncode != 0:
            return MCPResult.fail(
                f"Failed to revoke {permission}: {result.stderr.strip()}"
            )
        return MCPResult.success(None)
    except SystemMCPError as e:
        return MCPResult.fail(str(e))

def unlock_device() -> MCPResult:
    """Automatically unlocks the device using the PIN stored in memory."""
    import os
    import time
    try:
        # Check wakefulness
        power_res = adb.shell(["dumpsys", "power"])
        if power_res and hasattr(power_res, "stdout") and "mWakefulness=Asleep" in power_res.stdout:
            adb.shell(["input", "keyevent", "KEYCODE_WAKEUP"])
            time.sleep(1)
            
        # Check if locked
        keyguard_res = adb.shell(["dumpsys", "keyguard"])
        if keyguard_res and hasattr(keyguard_res, "stdout") and ("mShowing=true" in keyguard_res.stdout or "mShowingLockscreen=true" in keyguard_res.stdout):
            # Swipe up to reveal PIN pad
            adb.shell(["input", "swipe", "500", "1500", "500", "500", "300"])
            time.sleep(1.5)
            
            # Read PIN
            pin = "2442008" # Fallback
            profile_path = os.path.expanduser("~/.system-mcp/memory/user_profile.md")
            if os.path.exists(profile_path):
                with open(profile_path, "r", encoding="utf-8") as f:
                    for line in f:
                        if "Device PIN" in line or "laptop password" in line.lower():
                            parts = line.split(":")
                            if len(parts) > 1:
                                pin = parts[1].strip()
                                break
            
            # Type PIN
            adb.shell(["input", "text", pin])
            time.sleep(0.5)
            adb.shell(["input", "keyevent", "66"]) # ENTER
            time.sleep(1)
            
        return MCPResult.success("Unlock sequence completed.")
    except Exception as e:
        return MCPResult.fail(f"Failed to unlock device: {e}")

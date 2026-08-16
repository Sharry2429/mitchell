import ctypes
import json
import logging
import os
import platform
import re
import shutil
import subprocess
import time
import winreg
from typing import Any

import psutil

from mitchell.core.audit import check_destructive, log_action
from mitchell.windows.config import get_config
from mitchell.windows.core.powershell import execute as _ps_execute
from mitchell.windows.core.powershell import is_elevated
from mitchell.windows.types import (
    BatteryInfo,
    CommandResult,
    CpuInfo,
    DiskInfo,
    MemoryInfo,
    PowerPlan,
    ProcessInfo,
    RegistryValue,
    ServiceInfo,
    SystemInfo,
)

# --- power.py ---

__all__ = [
    "cancel_shutdown",
    "get_active_power_plan",
    "get_power_plans",
    "get_sleep_timeout",
    "hibernate",
    "lock_screen",
    "log_off",
    "restart",
    "set_power_plan",
    "set_sleep_timeout",
    "shutdown",
    "sleep",
]


def _run(cmd: list[str]) -> str:
    creationflags = getattr(subprocess, "CREATE_NO_WINDOW", 0x08000000)
    result = subprocess.run(
        cmd, capture_output=True, text=True, creationflags=creationflags
    )
    return result.stdout.strip()


def _run_bool(cmd: list[str]) -> bool:
    creationflags = getattr(subprocess, "CREATE_NO_WINDOW", 0x08000000)
    return subprocess.run(cmd, creationflags=creationflags).returncode == 0


def shutdown(delay: int = 0, force: bool = False, confirm: bool = False) -> bool:
    check_destructive("system.shutdown", confirm)
    config = get_config()
    if config.get("safeguards", True) and delay < 30:
        delay = 30
    cmd = ["shutdown", "/s", "/t", str(delay)]
    if force:
        cmd.append("/f")
    return _run_bool(cmd)


def restart(delay: int = 0, force: bool = False, confirm: bool = False) -> bool:
    check_destructive("system.restart", confirm)
    config = get_config()
    if config.get("safeguards", True) and delay < 30:
        delay = 30
    cmd = ["shutdown", "/r", "/t", str(delay)]
    if force:
        cmd.append("/f")
    return _run_bool(cmd)


def cancel_shutdown() -> bool:
    return _run_bool(["shutdown", "/a"])


def sleep() -> bool:
    cmd = [
        "powershell",
        "-NoProfile",
        "-Command",
        "Add-Type -Assembly System.Windows.Forms; [System.Windows.Forms.Application]::SetSuspendState('Suspend', $false, $false)",
    ]
    return _run_bool(cmd)


def hibernate(confirm: bool = False) -> bool:
    check_destructive("system.hibernate", confirm)
    return _run_bool(["shutdown", "/h"])


def lock_screen() -> bool:
    try:
        ctypes.windll.user32.LockWorkStation()
        return True
    except Exception:
        return False


def log_off(confirm: bool = False) -> bool:
    check_destructive("system.log_off", confirm)
    config = get_config()
    if config.get("safeguards", True):
        time.sleep(30)
    return _run_bool(["shutdown", "/l"])


def get_power_plans() -> list[PowerPlan]:
    output = _run(["powercfg", "/list"])
    plans = []
    for line in output.splitlines():
        if "Power Scheme GUID:" in line:
            parts = line.split()
            if len(parts) >= 4:
                guid = parts[3]
                name_match = re.search(r"\\((.*?)\\)", line)
                name = name_match.group(1) if name_match else "Unknown"
                is_active = "*" in line
                try:
                    plans.append(PowerPlan(guid=guid, name=name, is_active=is_active))
                except TypeError:
                    try:
                        plans.append(PowerPlan(guid, name, is_active))
                    except Exception:
                        pass
    return plans


def get_active_power_plan() -> PowerPlan | None:
    output = _run(["powercfg", "/getactivescheme"])
    if "Power Scheme GUID:" in output:
        parts = output.split()
        if len(parts) >= 4:
            guid = parts[3]
            name_match = re.search(r"\\((.*?)\\)", output)
            name = name_match.group(1) if name_match else "Unknown"
            try:
                return PowerPlan(guid=guid, name=name, is_active=True)
            except TypeError:
                try:
                    return PowerPlan(guid, name, True)
                except Exception:
                    return None
    return None


def set_power_plan(name_or_guid: str) -> bool:
    if re.match(r"^[0-9a-fA-F]{8}-([0-9a-fA-F]{4}-){3}[0-9a-fA-F]{12}$", name_or_guid):
        guid = name_or_guid
    else:
        plans = get_power_plans()
        guid = None
        for plan in plans:
            plan_name = getattr(plan, "name", "")
            if plan_name.lower() == name_or_guid.lower():
                guid = getattr(plan, "guid", "")
                break
        if not guid:
            return False

    return _run_bool(["powercfg", "/setactive", guid])


def get_sleep_timeout() -> dict[str, int]:
    output = _run(["powercfg", "/query", "SCHEME_CURRENT", "SUB_SLEEP", "STANDBYIDLE"])
    ac_timeout = 0
    dc_timeout = 0
    for line in output.splitlines():
        if "Current AC Power Setting Index:" in line:
            ac_timeout = int(line.split(":")[-1].strip(), 16) // 60
        elif "Current DC Power Setting Index:" in line:
            dc_timeout = int(line.split(":")[-1].strip(), 16) // 60
    return {"ac_minutes": ac_timeout, "dc_minutes": dc_timeout}


def set_sleep_timeout(
    ac_minutes: int | None = None, dc_minutes: int | None = None
) -> bool:
    success = True
    if ac_minutes is not None:
        if not _run_bool(
            ["powercfg", "/change", "standby-timeout-ac", str(ac_minutes)]
        ):
            success = False
    if dc_minutes is not None:
        if not _run_bool(
            ["powercfg", "/change", "standby-timeout-dc", str(dc_minutes)]
        ):
            success = False
    return success


# --- process.py ---


__all__ = [
    "get_process",
    "get_process_cpu",
    "get_process_memory",
    "is_process_running",
    "kill_process",
    "list_processes",
    "process_tree",
    "start_process",
]

CRITICAL_PROCESSES = {
    "csrss.exe",
    "lsass.exe",
    "winlogon.exe",
    "smss.exe",
    "services.exe",
    "svchost.exe",
    "system",
    "explorer.exe",
}


def _create_process_info(proc: psutil.Process) -> ProcessInfo:
    """Helper to convert psutil.Process to ProcessInfo."""
    try:
        mem_mb = proc.memory_info().rss / (1024 * 1024)
        cpu_percent = proc.cpu_percent()

        return ProcessInfo(
            pid=proc.pid,
            name=proc.name(),
            memory_mb=mem_mb,
            cpu_percent=cpu_percent,
            status=proc.status(),
        )
    except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
        return ProcessInfo(
            pid=proc.pid,
            name="unknown",
            memory_mb=0.0,
            cpu_percent=0.0,
            status="unknown",
        )


def list_processes(sort_by: str = "cpu") -> list[ProcessInfo]:
    """List all processes using psutil."""
    processes = []
    for proc in psutil.process_iter(
        ["pid", "name", "memory_info", "cpu_percent", "status"]
    ):
        try:
            processes.append(_create_process_info(proc))
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            pass

    if sort_by == "cpu":
        processes.sort(key=lambda x: x.cpu_percent, reverse=True)
    elif sort_by == "memory":
        processes.sort(key=lambda x: x.memory_mb, reverse=True)
    elif sort_by == "name":
        processes.sort(key=lambda x: x.name.lower() if x.name else "")

    return processes


def get_process(pid_or_name: int | str) -> ProcessInfo | None:
    """Get by PID or name."""
    if isinstance(pid_or_name, int) or (
        isinstance(pid_or_name, str) and pid_or_name.isdigit()
    ):
        pid = int(pid_or_name)
        try:
            proc = psutil.Process(pid)
            return _create_process_info(proc)
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            return None

    # Search by name
    name_lower = pid_or_name.lower()
    for proc in psutil.process_iter(["pid", "name"]):
        try:
            if proc.info["name"] and proc.info["name"].lower() == name_lower:
                return _create_process_info(proc)
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass

    return None


def kill_process(pid_or_name: int | str, force: bool = False, confirm: bool = False) -> bool:
    """Terminate/kill. If force=False (safeguards=True), block killing critical system processes."""
    check_destructive("process.kill", confirm)
    if isinstance(pid_or_name, int) or (
        isinstance(pid_or_name, str) and pid_or_name.isdigit()
    ):
        pid = int(pid_or_name)
        try:
            proc = psutil.Process(pid)
        except psutil.NoSuchProcess:
            return False
    else:
        # Search by name
        name_lower = pid_or_name.lower()
        proc = None
        for p in psutil.process_iter(["pid", "name"]):
            try:
                if p.info["name"] and p.info["name"].lower() == name_lower:
                    proc = p
                    break
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass

        if not proc:
            return False

    try:
        proc_name = proc.name().lower()

        if not force and proc_name in CRITICAL_PROCESSES:
            # Block killing critical processes
            return False

        proc.kill()
        return True
    except (psutil.NoSuchProcess, psutil.AccessDenied):
        return False


def start_process(command: str, cwd: str | None = None, confirm: bool = False) -> ProcessInfo:
    """Start new process."""
    check_destructive("shell.execute", confirm)
    log_action("windows.system", "start_process", {"command": command, "cwd": cwd}, {})
    try:
        # shell=True is intended here for raw command execution; gated by check_destructive above.
        proc = subprocess.Popen(command, shell=True, cwd=cwd)
        # Create a basic info object, we might not be able to get full psutil process immediately
        return ProcessInfo(
            pid=proc.pid,
            name=command.split()[0] if command else "unknown",
            memory_mb=0.0,
            cpu_percent=0.0,
            status="running",
        )
    except Exception:
        return ProcessInfo(
            pid=-1, name="error", memory_mb=0.0, cpu_percent=0.0, status="error"
        )


def process_tree(pid: int) -> list[ProcessInfo]:
    """Get parent and children."""
    tree = []
    try:
        proc = psutil.Process(pid)

        # Try to get parent
        parent = proc.parent()
        if parent:
            tree.append(_create_process_info(parent))

        # Add target process
        tree.append(_create_process_info(proc))

        # Add children
        for child in proc.children(recursive=True):
            tree.append(_create_process_info(child))

    except (psutil.NoSuchProcess, psutil.AccessDenied):
        pass

    return tree


def is_process_running(name: str) -> bool:
    """Check by name."""
    name_lower = name.lower()
    for proc in psutil.process_iter(["name"]):
        try:
            if proc.info["name"] and proc.info["name"].lower() == name_lower:
                return True
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass
    return False


def get_process_cpu(pid: int) -> float:
    """CPU percentage."""
    try:
        proc = psutil.Process(pid)
        return proc.cpu_percent()
    except (psutil.NoSuchProcess, psutil.AccessDenied):
        return 0.0


def get_process_memory(pid: int) -> float:
    """Memory in MB."""
    try:
        proc = psutil.Process(pid)
        return proc.memory_info().rss / (1024 * 1024)
    except (psutil.NoSuchProcess, psutil.AccessDenied):
        return 0.0


# --- shell.py ---


__all__ = [
    "cmd",
    "pipe",
    "powershell",
    "powershell_admin",
    "run_background",
    "run_script",
    "which",
]


def _check_safeguards(command: str) -> None:
    config = get_config()
    if not config.safeguards:
        return

    cmd_lower = command.lower()
    dangerous_patterns = [
        "format-volume",
        "format c:",
        "format-volume -driveletter c",
        "remove-item -path c:\\ -recurse -force",
        "remove-item -path c:/ -recurse -force",
        "del c:\\*.* /s /q",
    ]
    for pattern in dangerous_patterns:
        if pattern in cmd_lower:
            raise ValueError(
                f"Command blocked by safeguards: matches dangerous pattern '{pattern}'"
            )


def powershell(
    command: str, timeout: int | None = None, encoding: str | None = None
) -> CommandResult:
    """Execute a PowerShell command."""
    kwargs = {}
    if timeout is not None:
        kwargs["timeout"] = timeout
    if encoding is not None:
        kwargs["encoding"] = encoding
    return _ps_execute(command, **kwargs)


def powershell_admin(command: str, timeout: int | None = None) -> CommandResult:
    """Execute PowerShell with admin elevation."""
    _check_safeguards(command)

    if is_elevated():
        return powershell(command, timeout=timeout)
    else:
        admin_command = f'Start-Process powershell -Verb RunAs -ArgumentList "-NoProfile", "-Command", "{command}" -Wait -NoNewWindow'
        return _ps_execute(admin_command, timeout=timeout)


def cmd(command: str, timeout: int | None = None) -> CommandResult:
    """Execute a CMD command via subprocess."""
    try:
        process = subprocess.run(
            f"cmd.exe /c {command}",
            capture_output=True,
            text=True,
            timeout=timeout,
            shell=False,
        )
        return CommandResult(
            stdout=process.stdout, stderr=process.stderr, exit_code=process.returncode
        )
    except subprocess.TimeoutExpired as e:
        stdout = (
            e.stdout.decode() if isinstance(e.stdout, bytes) else str(e.stdout or "")
        )
        stderr = (
            e.stderr.decode() if isinstance(e.stderr, bytes) else str(e.stderr or "")
        )
        return CommandResult(stdout=stdout, stderr=stderr, exit_code=-1)


def run_script(
    path: str, args: list[str] | None = None, timeout: int | None = None
) -> CommandResult:
    """Run a .ps1, .bat, .cmd, or .py script file."""
    if not os.path.exists(path):
        return CommandResult(
            stdout="", stderr=f"Script not found: {path}", exit_code=-1
        )

    ext = os.path.splitext(path)[1].lower()
    args_str = " ".join([f'"{a}"' for a in args]) if args else ""

    if ext == ".ps1":
        cmd_str = f'& "{path}" {args_str}'
        return powershell(cmd_str, timeout=timeout)
    elif ext in [".bat", ".cmd"]:
        cmd_str = f'"{path}" {args_str}'
        return cmd(cmd_str, timeout=timeout)
    elif ext == ".py":
        cmd_str = f'python "{path}" {args_str}'
        return cmd(cmd_str, timeout=timeout)
    else:
        return CommandResult(
            stdout="", stderr=f"Unsupported script extension: {ext}", exit_code=-1
        )


def run_background(command: str, shell: str = "powershell") -> ProcessInfo:
    """Start a command as a background process, return process info."""
    if shell.lower() == "powershell":
        process = subprocess.Popen(
            ["powershell.exe", "-NoProfile", "-Command", command],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    else:
        process = subprocess.Popen(
            f"cmd.exe /c {command}",
            shell=False,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )

    return ProcessInfo(pid=process.pid, name=shell)


def pipe(commands: list[str], shell: str = "powershell") -> CommandResult:
    """Chain multiple commands with pipe operator."""
    chained = " | ".join(commands)
    if shell.lower() == "powershell":
        return powershell(chained)
    else:
        return cmd(chained)


def which(program: str) -> str | None:
    """Find the full path of an executable (like Unix 'which')."""
    return shutil.which(program)


# --- sysinfo.py ---

__all__ = [
    "get_battery_info",
    "get_cpu_info",
    "get_cpu_usage",
    "get_disk_info",
    "get_environment_variables",
    "get_event_log",
    "get_installed_programs",
    "get_memory_info",
    "get_startup_programs",
    "get_system_info",
    "get_uptime",
    "get_uptime_human",
    "get_windows_version",
    "set_environment_variable",
]


def get_cpu_info() -> CpuInfo:
    return CpuInfo(
        brand=platform.processor(),
        cores_physical=psutil.cpu_count(logical=False),
        cores_logical=psutil.cpu_count(logical=True),
        freq_current=psutil.cpu_freq().current if psutil.cpu_freq() else 0.0,
        freq_max=psutil.cpu_freq().max if psutil.cpu_freq() else 0.0,
    )


def get_cpu_usage(interval: float = 1.0) -> float:
    return psutil.cpu_percent(interval=interval)


def get_memory_info() -> MemoryInfo:
    mem = psutil.virtual_memory()
    swap = psutil.swap_memory()
    return MemoryInfo(
        total=mem.total,
        available=mem.available,
        used=mem.used,
        percent=mem.percent,
        swap_total=swap.total,
        swap_used=swap.used,
        swap_percent=swap.percent,
    )


def get_disk_info() -> list[DiskInfo]:
    disks = []
    for part in psutil.disk_partitions(all=False):
        if os.name == "nt" and ("cdrom" in part.opts or part.fstype == ""):
            continue
        try:
            usage = psutil.disk_usage(part.mountpoint)
            disks.append(
                DiskInfo(
                    device=part.device,
                    mountpoint=part.mountpoint,
                    fstype=part.fstype,
                    total=usage.total,
                    used=usage.used,
                    free=usage.free,
                    percent=usage.percent,
                )
            )
        except PermissionError:
            continue
    return disks


def get_battery_info() -> BatteryInfo:
    battery = psutil.sensors_battery()
    if battery:
        return BatteryInfo(
            percent=battery.percent,
            secsleft=battery.secsleft,
            power_plugged=battery.power_plugged,
        )
    return BatteryInfo(percent=100.0, secsleft=0, power_plugged=True)


def get_uptime() -> float:
    return time.time() - psutil.boot_time()


def get_uptime_human() -> str:
    uptime_secs = get_uptime()
    hours, remainder = divmod(uptime_secs, 3600)
    minutes, seconds = divmod(remainder, 60)
    return f"{int(hours)}h {int(minutes)}m {int(seconds)}s"


def get_environment_variables() -> dict[str, str]:
    return dict(os.environ)


def set_environment_variable(name: str, value: str, scope: str = "user", confirm: bool = False) -> bool:
    check_destructive("registry.write", confirm)
    log_action("windows.system", "set_environment_variable", {"name": name, "scope": scope}, {})
    config = get_config()
    if config.get("safeguards", True) and scope == "system":
        return False

    try:
        if scope == "user":
            key = winreg.OpenKey(
                winreg.HKEY_CURRENT_USER, r"Environment", 0, winreg.KEY_SET_VALUE
            )
        else:
            key = winreg.OpenKey(
                winreg.HKEY_LOCAL_MACHINE,
                r"SYSTEM\CurrentControlSet\Control\Session Manager\Environment",
                0,
                winreg.KEY_SET_VALUE,
            )

        winreg.SetValueEx(key, name, 0, winreg.REG_SZ, value)
        winreg.CloseKey(key)
        return True
    except Exception:
        return False


def get_installed_programs() -> list[dict[str, str]]:
    programs = []
    keys_to_check = [
        (
            winreg.HKEY_LOCAL_MACHINE,
            r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall",
        ),
        (
            winreg.HKEY_LOCAL_MACHINE,
            r"SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall",
        ),
        (
            winreg.HKEY_CURRENT_USER,
            r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall",
        ),
    ]

    for hkey, key_path in keys_to_check:
        try:
            with winreg.OpenKey(hkey, key_path) as key:
                for i in range(winreg.QueryInfoKey(key)[0]):
                    try:
                        sub_key_name = winreg.EnumKey(key, i)
                        with winreg.OpenKey(key, sub_key_name) as sub_key:
                            try:
                                display_name = winreg.QueryValueEx(
                                    sub_key, "DisplayName"
                                )[0]
                                version = ""
                                try:
                                    version = winreg.QueryValueEx(
                                        sub_key, "DisplayVersion"
                                    )[0]
                                except FileNotFoundError:
                                    pass
                                programs.append(
                                    {"name": display_name, "version": version}
                                )
                            except FileNotFoundError:
                                continue
                    except OSError:
                        continue
        except FileNotFoundError:
            continue
    return programs


def get_windows_version() -> dict[str, str]:
    try:
        return {
            "system": platform.system(),
            "release": platform.release(),
            "version": platform.version(),
            "machine": platform.machine(),
            "architecture": platform.architecture()[0],
        }
    except Exception:
        return {}


def get_event_log(source: str = "System", count: int = 10) -> list[dict]:
    try:
        cmd = [
            "powershell",
            "-NoProfile",
            "-Command",
            f"Get-EventLog -LogName {source} -Newest {count} | Select-Object EventID, MachineName, Source, Message, TimeGenerated | ConvertTo-Json",
        ]
        output = subprocess.check_output(
            cmd, creationflags=subprocess.CREATE_NO_WINDOW
        ).decode("utf-8", errors="ignore")
        if not output.strip():
            return []

        import json

        logs = json.loads(output)
        if not isinstance(logs, list):
            logs = [logs]
        return logs
    except Exception:
        return []


def get_startup_programs() -> list[dict[str, str]]:
    programs = []
    keys_to_check = [
        (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Windows\CurrentVersion\Run"),
        (
            winreg.HKEY_LOCAL_MACHINE,
            r"SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Run",
        ),
        (winreg.HKEY_CURRENT_USER, r"SOFTWARE\Microsoft\Windows\CurrentVersion\Run"),
    ]

    for hkey, key_path in keys_to_check:
        try:
            with winreg.OpenKey(hkey, key_path) as key:
                for i in range(winreg.QueryInfoKey(key)[1]):
                    try:
                        name, value, _ = winreg.EnumValue(key, i)
                        programs.append({"name": name, "command": value})
                    except OSError:
                        continue
        except FileNotFoundError:
            continue
    return programs


def get_system_info() -> SystemInfo:
    return SystemInfo(
        cpu=get_cpu_info(),
        memory=get_memory_info(),
        disks=get_disk_info(),
        battery=get_battery_info(),
        uptime=get_uptime(),
        windows_version=get_windows_version(),
    )


# --- registry.py ---


__all__ = [
    "reg_create_key",
    "reg_delete",
    "reg_delete_key",
    "reg_key_exists",
    "reg_list_keys",
    "reg_list_values",
    "reg_read",
    "reg_write",
]

HIVE_MAP = {
    "HKLM": winreg.HKEY_LOCAL_MACHINE,
    "HKEY_LOCAL_MACHINE": winreg.HKEY_LOCAL_MACHINE,
    "HKCU": winreg.HKEY_CURRENT_USER,
    "HKEY_CURRENT_USER": winreg.HKEY_CURRENT_USER,
    "HKCR": winreg.HKEY_CLASSES_ROOT,
    "HKEY_CLASSES_ROOT": winreg.HKEY_CLASSES_ROOT,
    "HKU": winreg.HKEY_USERS,
    "HKEY_USERS": winreg.HKEY_USERS,
    "HKCC": winreg.HKEY_CURRENT_CONFIG,
    "HKEY_CURRENT_CONFIG": winreg.HKEY_CURRENT_CONFIG,
}

TYPE_MAP = {
    "REG_SZ": winreg.REG_SZ,
    "REG_DWORD": winreg.REG_DWORD,
    "REG_BINARY": winreg.REG_BINARY,
    "REG_EXPAND_SZ": winreg.REG_EXPAND_SZ,
    "REG_MULTI_SZ": winreg.REG_MULTI_SZ,
    "REG_QWORD": winreg.REG_QWORD,
}
TYPE_MAP_REV = {v: k for k, v in TYPE_MAP.items()}

CRITICAL_KEYS = ["software\\microsoft\\windows", "system\\currentcontrolset"]


def _parse_key_path(key_path: str) -> tuple[int, str]:
    parts = key_path.replace("/", "\\").split("\\", 1)
    hive_name = parts[0].upper()
    subkey = parts[1] if len(parts) > 1 else ""
    if hive_name not in HIVE_MAP:
        raise ValueError(f"Invalid registry hive: {hive_name}")
    return HIVE_MAP[hive_name], subkey


def _is_critical_key(key_path: str) -> bool:
    path_lower = key_path.lower()
    for crit in CRITICAL_KEYS:
        if crit in path_lower:
            return True
    return False


def _check_safeguard(key_path: str):
    config = get_config()
    if config.safeguards and _is_critical_key(key_path):
        raise PermissionError(
            f"Safeguard blocked write to critical registry key: {key_path}"
        )


def reg_read(key_path: str, value_name: str = "") -> RegistryValue:
    hive, subkey = _parse_key_path(key_path)
    try:
        with winreg.OpenKey(hive, subkey, 0, winreg.KEY_READ) as key:
            value, reg_type = winreg.QueryValueEx(key, value_name)
            type_str = TYPE_MAP_REV.get(reg_type, f"UNKNOWN_{reg_type}")
            return RegistryValue(name=value_name, data=value, type=type_str)
    except FileNotFoundError:
        raise FileNotFoundError(f"Registry value not found: {key_path}\\{value_name}")


def reg_write(
    key_path: str, value_name: str, value_data: Any, value_type: str = "REG_SZ", confirm: bool = False
) -> bool:
    check_destructive("registry.write", confirm)
    log_action("windows.system", "reg_write", {"key_path": key_path, "value_name": value_name}, {})
    _check_safeguard(key_path)
    hive, subkey = _parse_key_path(key_path)
    if value_type not in TYPE_MAP:
        raise ValueError(f"Unsupported registry type: {value_type}")

    try:
        with winreg.OpenKey(hive, subkey, 0, winreg.KEY_SET_VALUE) as key:
            winreg.SetValueEx(key, value_name, 0, TYPE_MAP[value_type], value_data)
            return True
    except FileNotFoundError:
        raise FileNotFoundError(f"Registry key not found: {key_path}")


def reg_delete(key_path: str, value_name: str, confirm: bool = False) -> bool:
    check_destructive("registry.write", confirm)
    log_action("windows.system", "reg_delete", {"key_path": key_path, "value_name": value_name}, {})
    _check_safeguard(key_path)
    hive, subkey = _parse_key_path(key_path)
    try:
        with winreg.OpenKey(hive, subkey, 0, winreg.KEY_SET_VALUE) as key:
            winreg.DeleteValue(key, value_name)
            return True
    except FileNotFoundError:
        return False


def reg_list_keys(key_path: str) -> list[str]:
    hive, subkey = _parse_key_path(key_path)
    keys = []
    try:
        with winreg.OpenKey(hive, subkey, 0, winreg.KEY_READ) as key:
            i = 0
            while True:
                try:
                    keys.append(winreg.EnumKey(key, i))
                    i += 1
                except OSError:
                    break
    except FileNotFoundError:
        pass
    return keys


def reg_list_values(key_path: str) -> list[RegistryValue]:
    hive, subkey = _parse_key_path(key_path)
    values = []
    try:
        with winreg.OpenKey(hive, subkey, 0, winreg.KEY_READ) as key:
            i = 0
            while True:
                try:
                    name, data, type_id = winreg.EnumValue(key, i)
                    type_str = TYPE_MAP_REV.get(type_id, f"UNKNOWN_{type_id}")
                    values.append(RegistryValue(name=name, data=data, type=type_str))
                    i += 1
                except OSError:
                    break
    except FileNotFoundError:
        pass
    return values


def reg_key_exists(key_path: str) -> bool:
    hive, subkey = _parse_key_path(key_path)
    try:
        with winreg.OpenKey(hive, subkey, 0, winreg.KEY_READ):
            return True
    except FileNotFoundError:
        return False


def reg_create_key(key_path: str, confirm: bool = False) -> bool:
    check_destructive("registry.write", confirm)
    log_action("windows.system", "reg_create_key", {"key_path": key_path}, {})
    _check_safeguard(key_path)
    hive, subkey = _parse_key_path(key_path)
    try:
        with winreg.CreateKey(hive, subkey):
            return True
    except Exception as e:
        logging.error(f"Failed to create key: {e}")
        return False


def reg_delete_key(key_path: str, recursive: bool = False, confirm: bool = False) -> bool:
    check_destructive("registry.write", confirm)
    log_action("windows.system", "reg_delete_key", {"key_path": key_path, "recursive": recursive}, {})
    _check_safeguard(key_path)
    hive, subkey = _parse_key_path(key_path)

    def _delete_recursive(h, sub):
        try:
            with winreg.OpenKey(h, sub, 0, winreg.KEY_ALL_ACCESS) as key:
                while True:
                    try:
                        child = winreg.EnumKey(key, 0)
                        _delete_recursive(h, f"{sub}\\{child}")
                    except OSError:
                        break
            winreg.DeleteKey(h, sub)
        except FileNotFoundError:
            pass

    try:
        if recursive:
            _delete_recursive(hive, subkey)
        else:
            winreg.DeleteKey(hive, subkey)
        return True
    except Exception as e:
        logging.error(f"Failed to delete key: {e}")
        return False


# --- services.py ---

__all__ = [
    "get_service",
    "get_service_config",
    "get_service_status",
    "is_service_running",
    "list_services",
    "restart_service",
    "set_service_startup",
    "start_service",
    "stop_service",
]


def list_services(status_filter: str | None = None) -> list[ServiceInfo]:
    try:
        cmd = [
            "powershell",
            "-NoProfile",
            "-Command",
            "Get-Service | Select-Object Name, DisplayName, Status, StartType | ConvertTo-Json",
        ]
        output = subprocess.check_output(
            cmd, creationflags=subprocess.CREATE_NO_WINDOW
        ).decode("utf-8", errors="ignore")
        if not output.strip():
            return []

        services_data = json.loads(output)
        if not isinstance(services_data, list):
            services_data = [services_data]

        services = []
        for svc in services_data:
            # Map statuses approximately based on PowerShell output format
            status = str(svc.get("Status", ""))
            status_str = (
                "Running"
                if status == "4" or status == "Running"
                else "Stopped" if status == "1" or status == "Stopped" else "Unknown"
            )

            start_type = str(svc.get("StartType", ""))
            start_type_str = (
                "Auto"
                if start_type == "2" or start_type == "Automatic"
                else (
                    "Manual"
                    if start_type == "3" or start_type == "Manual"
                    else (
                        "Disabled"
                        if start_type == "4" or start_type == "Disabled"
                        else "Unknown"
                    )
                )
            )

            if status_filter and status_filter.lower() != status_str.lower():
                continue

            services.append(
                ServiceInfo(
                    name=svc.get("Name", ""),
                    display_name=svc.get("DisplayName", ""),
                    status=status_str,
                    start_type=start_type_str,
                )
            )
        return services
    except Exception:
        return []


def get_service(name: str) -> ServiceInfo | None:
    services = list_services()
    for svc in services:
        if svc.name.lower() == name.lower():
            return svc
    return None


def start_service(name: str) -> bool:
    config = get_config()
    if config.get("safeguards", True):
        pass  # Handle warnings upstream
    try:
        subprocess.check_call(
            ["sc", "start", name], creationflags=subprocess.CREATE_NO_WINDOW
        )
        return True
    except Exception:
        return False


def stop_service(name: str) -> bool:
    config = get_config()
    if config.get("safeguards", True):
        critical_services = ["RpcSs", "DcomLaunch", "SamSs"]
        if name in critical_services:
            return False
    try:
        subprocess.check_call(
            ["sc", "stop", name], creationflags=subprocess.CREATE_NO_WINDOW
        )
        return True
    except Exception:
        return False


def restart_service(name: str) -> bool:
    if stop_service(name):
        return start_service(name)
    return False


def get_service_status(name: str) -> str:
    svc = get_service(name)
    if svc:
        return svc.status
    return "Unknown"


def set_service_startup(name: str, startup_type: str) -> bool:
    type_map = {"auto": "auto", "manual": "demand", "disabled": "disabled"}
    sc_type = type_map.get(startup_type.lower())
    if not sc_type:
        return False
    try:
        subprocess.check_call(
            ["sc", "config", name, f"start={sc_type}"],
            creationflags=subprocess.CREATE_NO_WINDOW,
        )
        return True
    except Exception:
        return False


def is_service_running(name: str) -> bool:
    return get_service_status(name).lower() == "running"


def get_service_config(name: str) -> dict:
    try:
        output = subprocess.check_output(
            ["sc", "qc", name], creationflags=subprocess.CREATE_NO_WINDOW
        ).decode("utf-8", errors="ignore")
        config = {}
        for line in output.splitlines():
            if ":" in line:
                key, val = line.split(":", 1)
                config[key.strip()] = val.strip()
        return config
    except Exception:
        return {}


# --- vdm.py ---

__all__.extend([
    "get_all_desktops",
    "get_current_desktop",
    "get_desktop_count",
    "is_window_on_current_desktop",
    "move_window_to_desktop",
    "switch_desktop",
])

from mitchell.windows.core import vdm

def get_all_desktops() -> list[dict[str, str]]:
    """Get all virtual desktops."""
    return vdm.get_all_desktops()

def get_current_desktop() -> dict[str, str]:
    """Get the current virtual desktop info."""
    return vdm.get_current_desktop()

def get_desktop_count() -> int:
    """Get the number of virtual desktops."""
    return vdm.get_desktop_count()

def is_window_on_current_desktop(hwnd: int) -> bool:
    """Check if a window is on the current virtual desktop."""
    return vdm.is_window_on_current_desktop(hwnd)

def move_window_to_desktop(hwnd: int, desktop_index: int) -> bool:
    """Move a window to a specific virtual desktop."""
    return vdm.move_window_to_desktop(hwnd, desktop_index)

def switch_desktop(index: int) -> bool:
    """Switch to a virtual desktop by index (0-based)."""
    return vdm.switch_desktop(index)

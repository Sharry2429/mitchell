import ctypes
import json
import logging
import os
import socket
import subprocess
import tempfile
import urllib.request

import psutil

from mitchell.core.errors import SystemMCPError
from mitchell.windows.config import get_config
from mitchell.windows.types import (
    AudioDevice,
    DisplayInfo,
    DnsResult,
    NetworkAdapter,
    NetworkInfo,
    PingResult,
    PortInfo,
)

# --- audio.py ---

__all__ = [
    "get_audio_devices",
    "get_volume",
    "is_muted",
    "mute",
    "set_default_device",
    "set_volume",
    "toggle_mute",
    "unmute",
    "volume_down",
    "volume_up",
]

VK_VOLUME_MUTE = 0xAD
VK_VOLUME_DOWN = 0xAE
VK_VOLUME_UP = 0xAF
KEYEVENTF_KEYUP = 0x0002


def _press_key(vk_code: int):
    ctypes.windll.user32.keybd_event(vk_code, 0, 0, 0)
    ctypes.windll.user32.keybd_event(vk_code, 0, KEYEVENTF_KEYUP, 0)


def _run_powershell(script: str) -> str:
    creationflags = getattr(subprocess, "CREATE_NO_WINDOW", 0x08000000)
    result = subprocess.run(
        ["powershell", "-NoProfile", "-Command", script],
        capture_output=True,
        text=True,
        creationflags=creationflags,
    )
    return result.stdout.strip()


# C# snippet for CoreAudioApi to handle absolute volume and mute state
PS_AUDIO_SCRIPT = """
$code = @"
using System.Runtime.InteropServices;
namespace Audio {
    [Guid("5CDF2C82-841E-4546-9722-0CF74078229A"), InterfaceType(ComInterfaceType.InterfaceIsIUnknown)]
    interface IAudioEndpointVolume {
        int f(); int g(); int h(); int i();
        int SetMasterVolumeLevelScalar(float fLevel, System.Guid pguidEventContext);
        int j();
        int GetMasterVolumeLevelScalar(out float pfLevel);
        int k(); int l(); int m(); int n();
        int SetMute([MarshalAs(UnmanagedType.Bool)] bool bMute, System.Guid pguidEventContext);
        int GetMute(out bool pbMute);
    }
    [Guid("D666063F-1587-4E43-81F1-B948E807363F"), InterfaceType(ComInterfaceType.InterfaceIsIUnknown)]
    interface IMMDevice {
        int Activate(ref System.Guid id, int clsCtx, int activationParams, out IAudioEndpointVolume aev);
    }
    [Guid("A95664D2-9614-4F35-A746-DE8DB63617E6"), InterfaceType(ComInterfaceType.InterfaceIsIUnknown)]
    interface IMMDeviceEnumerator {
        int f();
        int GetDefaultAudioEndpoint(int dataFlow, int role, out IMMDevice endpoint);
    }
    [ComImport, Guid("BCDE0395-E52F-467C-8E3D-C4579291692E")] class MMDeviceEnumeratorComObject { }
    public class Volume {
        static IAudioEndpointVolume Vol() {
            var enumerator = new MMDeviceEnumeratorComObject() as IMMDeviceEnumerator;
            IMMDevice dev = null;
            Marshal.ThrowExceptionForHR(enumerator.GetDefaultAudioEndpoint(0, 1, out dev));
            IAudioEndpointVolume epv = null;
            var epvid = typeof(IAudioEndpointVolume).GUID;
            Marshal.ThrowExceptionForHR(dev.Activate(ref epvid, 23, 0, out epv));
            return epv;
        }
        public static float Get() {
            float v = -1;
            Marshal.ThrowExceptionForHR(Vol().GetMasterVolumeLevelScalar(out v));
            return v * 100;
        }
        public static void Set(float v) {
            Marshal.ThrowExceptionForHR(Vol().SetMasterVolumeLevelScalar(v / 100, System.Guid.Empty));
        }
        public static bool GetMute() {
            bool m;
            Marshal.ThrowExceptionForHR(Vol().GetMute(out m));
            return m;
        }
        public static void SetMute(bool m) {
            Marshal.ThrowExceptionForHR(Vol().SetMute(m, System.Guid.Empty));
        }
    }
}
"@
Add-Type -TypeDefinition $code -IgnoreWarnings
"""


def get_volume() -> float:
    """Get system volume 0-100."""
    script = PS_AUDIO_SCRIPT + "\\n[Audio.Volume]::Get()"
    try:
        val = _run_powershell(script)
        return float(val.replace(",", "."))
    except Exception as e:
        raise SystemMCPError("Failed to read system volume") from e


def set_volume(level: int) -> None:
    """Set system volume 0-100."""
    level = max(0, min(100, level))
    script = PS_AUDIO_SCRIPT + f"\\n[Audio.Volume]::Set({level})"
    _run_powershell(script)


def mute() -> None:
    """Mute system."""
    if not is_muted():
        _press_key(VK_VOLUME_MUTE)


def unmute() -> None:
    """Unmute system."""
    if is_muted():
        _press_key(VK_VOLUME_MUTE)


def toggle_mute() -> None:
    """Toggle mute system."""
    _press_key(VK_VOLUME_MUTE)


def is_muted() -> bool:
    """Check mute state."""
    script = PS_AUDIO_SCRIPT + "\\n[Audio.Volume]::GetMute()"
    val = _run_powershell(script).strip().lower()
    return val == "true"


def volume_up(steps: int = 2) -> None:
    """Increase volume using VK_VOLUME_UP key."""
    for _ in range(steps):
        _press_key(VK_VOLUME_UP)


def volume_down(steps: int = 2) -> None:
    """Decrease volume using VK_VOLUME_DOWN key."""
    for _ in range(steps):
        _press_key(VK_VOLUME_DOWN)


def get_audio_devices() -> list[AudioDevice]:
    """Get audio devices."""
    script = "Get-CimInstance Win32_SoundDevice | Select-Object Name, Status, Manufacturer | ConvertTo-Json"
    output = _run_powershell(script)
    if not output:
        return []
    try:
        data = json.loads(output)
        if isinstance(data, dict):
            data = [data]
        devices = []
        for item in data:
            devices.append(
                AudioDevice(
                    id=item.get("Name", ""),
                    name=item.get("Name", ""),
                    is_default=False,
                    device_type="output",
                )
            )
        return devices
    except Exception:
        return []


def set_default_device(name: str) -> bool:
    """Set default audio device.
    Note: Requires a third-party COM library (nircmd or AudioDeviceCmdlets).
    Known limitation.
    """
    return False


# --- display.py ---


__all__ = [
    "get_brightness",
    "get_display_resolution",
    "get_displays",
    "get_dpi_scale",
    "get_primary_display",
    "get_screen_size",
    "set_brightness",
]


def get_displays() -> list[DisplayInfo]:
    displays = []

    def monitor_enum_proc(hMonitor, hdcMonitor, lprcMonitor, dwData):
        displays.append(DisplayInfo(handle=hMonitor))
        return 1

    MonitorEnumProc = ctypes.WINFUNCTYPE(
        ctypes.c_int,
        ctypes.c_void_p,
        ctypes.c_void_p,
        ctypes.POINTER(ctypes.c_void_p),
        ctypes.c_void_p,
    )
    ctypes.windll.user32.EnumDisplayMonitors(
        None, None, MonitorEnumProc(monitor_enum_proc), 0
    )

    return displays


def get_primary_display() -> DisplayInfo:
    return DisplayInfo(handle=0, is_primary=True)


def get_display_resolution() -> tuple[int, int]:
    user32 = ctypes.windll.user32
    width = user32.GetSystemMetrics(0)
    height = user32.GetSystemMetrics(1)
    return width, height


def get_dpi_scale() -> float:
    try:
        user32 = ctypes.windll.user32
        user32.SetProcessDPIAware()
        dpi = ctypes.windll.user32.GetDpiForSystem()
        return dpi / 96.0
    except AttributeError:
        return 1.0


def get_screen_size() -> tuple[int, int]:
    user32 = ctypes.windll.user32
    width = user32.GetSystemMetrics(78)  # SM_CXVIRTUALSCREEN
    height = user32.GetSystemMetrics(79)  # SM_CYVIRTUALSCREEN
    return width, height


def set_brightness(level: int) -> bool:
    if not (0 <= level <= 100):
        raise ValueError("Brightness must be between 0 and 100")

    ps_command = f"(Get-WmiObject -Namespace root/WMI -Class WmiMonitorBrightnessMethods).WmiSetBrightness(1,{level})"
    try:
        result = subprocess.run(
            ["powershell", "-Command", ps_command], capture_output=True, text=True
        )
        return result.returncode == 0
    except Exception as e:
        logging.error(f"Failed to set brightness: {e}")
        return False


def get_brightness() -> int:
    ps_command = "(Get-WmiObject -Namespace root/WMI -Class WmiMonitorBrightness).CurrentBrightness"
    try:
        result = subprocess.run(
            ["powershell", "-Command", ps_command], capture_output=True, text=True
        )
        if result.returncode == 0 and result.stdout.strip().isdigit():
            return int(result.stdout.strip())
        return -1
    except Exception as e:
        logging.error(f"Failed to get brightness: {e}")
        return -1


# --- network.py ---

__all__ = [
    "add_firewall_rule",
    "connect_wifi",
    "disconnect_wifi",
    "dns_lookup",
    "flush_dns",
    "get_firewall_status",
    "get_ip_addresses",
    "get_network_adapters",
    "get_network_info",
    "get_open_ports",
    "get_public_ip",
    "get_wifi_networks",
    "ping",
    "remove_firewall_rule",
    "traceroute",
]


def get_network_adapters() -> list[NetworkAdapter]:
    adapters = []
    if_addrs = psutil.net_if_addrs()
    if_stats = psutil.net_if_stats()
    for name, addrs in if_addrs.items():
        stats = if_stats.get(name)
        ip = None
        mac = None
        for addr in addrs:
            if addr.family == socket.AF_INET:
                ip = addr.address
            elif addr.family == psutil.AF_LINK:
                mac = addr.address
        adapters.append(
            NetworkAdapter(
                name=name,
                ip_address=ip or "",
                mac_address=mac or "",
                is_up=stats.isup if stats else False,
                speed=stats.speed if stats else 0,
            )
        )
    return adapters


def get_network_info() -> NetworkInfo:
    return NetworkInfo(
        hostname=socket.gethostname(),
        adapters=get_network_adapters(),
        public_ip=get_public_ip(),
    )


def get_ip_addresses() -> dict[str, list[str]]:
    ips = {}
    for name, addrs in psutil.net_if_addrs().items():
        ips[name] = [addr.address for addr in addrs if addr.family == socket.AF_INET]
    return ips


def get_public_ip() -> str:
    try:
        req = urllib.request.Request("https://api.ipify.org")
        with urllib.request.urlopen(req, timeout=5) as response:
            return response.read().decode("utf-8").strip()
    except Exception:
        return ""


def get_wifi_networks() -> list[dict[str, str]]:
    try:
        output = subprocess.check_output(
            ["netsh", "wlan", "show", "networks", "mode=bssid"],
            creationflags=subprocess.CREATE_NO_WINDOW,
        ).decode("utf-8", errors="ignore")
        networks = []
        current_ssid = None
        for line in output.splitlines():
            line = line.strip()
            if line.startswith("SSID"):
                parts = line.split(":", 1)
                if len(parts) > 1:
                    current_ssid = parts[1].strip()
                    networks.append({"ssid": current_ssid})
            elif line.startswith("Authentication") and current_ssid:
                networks[-1]["auth"] = line.split(":", 1)[1].strip()
            elif line.startswith("Encryption") and current_ssid:
                networks[-1]["encryption"] = line.split(":", 1)[1].strip()
        return networks
    except Exception:
        return []


def connect_wifi(ssid: str, password: str | None = None) -> bool:
    try:
        if password:
            profile_xml = f"""<?xml version="1.0"?>
<WLANProfile xmlns="http://www.microsoft.com/networking/WLAN/profile/v1">
    <name>{ssid}</name>
    <SSIDConfig>
        <SSID>
            <name>{ssid}</name>
        </SSID>
    </SSIDConfig>
    <connectionType>ESS</connectionType>
    <connectionMode>auto</connectionMode>
    <MSM>
        <security>
            <authEncryption>
                <authentication>WPA2PSK</authentication>
                <encryption>AES</encryption>
                <useOneX>false</useOneX>
            </authEncryption>
            <sharedKey>
                <keyType>passPhrase</keyType>
                <protected>false</protected>
                <keyMaterial>{password}</keyMaterial>
            </sharedKey>
        </security>
    </MSM>
</WLANProfile>"""
            fd, path = tempfile.mkstemp(suffix=".xml")
            with os.fdopen(fd, "w") as f:
                f.write(profile_xml)
            subprocess.check_call(
                ["netsh", "wlan", "add", "profile", "filename=" + path],
                creationflags=subprocess.CREATE_NO_WINDOW,
            )
            os.remove(path)

        subprocess.check_call(
            ["netsh", "wlan", "connect", "name=" + ssid],
            creationflags=subprocess.CREATE_NO_WINDOW,
        )
        return True
    except Exception:
        return False


def disconnect_wifi() -> bool:
    try:
        subprocess.check_call(
            ["netsh", "wlan", "disconnect"], creationflags=subprocess.CREATE_NO_WINDOW
        )
        return True
    except Exception:
        return False


def ping(host: str, count: int = 4, timeout: int = 5) -> PingResult:
    try:
        output = subprocess.check_output(
            ["ping", "-n", str(count), "-w", str(timeout * 1000), host],
            creationflags=subprocess.CREATE_NO_WINDOW,
        ).decode("utf-8", errors="ignore")
        return PingResult(success=True, output=output)
    except subprocess.CalledProcessError as e:
        return PingResult(
            success=False, output=e.output.decode("utf-8", errors="ignore")
        )


def traceroute(host: str, max_hops: int = 30) -> list[dict]:
    try:
        output = subprocess.check_output(
            ["tracert", "-h", str(max_hops), host],
            creationflags=subprocess.CREATE_NO_WINDOW,
        ).decode("utf-8", errors="ignore")
        hops = []
        for line in output.splitlines():
            if line.strip() and line.strip()[0].isdigit():
                hops.append({"hop": line.strip()})
        return hops
    except Exception:
        return []


def get_open_ports(pid: int | None = None) -> list[PortInfo]:
    ports = []
    for conn in psutil.net_connections():
        if conn.status == "LISTEN":
            if pid and conn.pid != pid:
                continue
            ports.append(
                PortInfo(
                    port=conn.laddr.port,
                    protocol="TCP" if conn.type == socket.SOCK_STREAM else "UDP",
                    pid=conn.pid,
                    address=conn.laddr.ip,
                )
            )
    return ports


def dns_lookup(domain: str) -> DnsResult:
    try:
        addrs = socket.getaddrinfo(domain, None)
        ips = list(set([addr[4][0] for addr in addrs]))
        return DnsResult(domain=domain, ips=ips)
    except Exception:
        return DnsResult(domain=domain, ips=[])


def get_firewall_status() -> dict[str, str]:
    try:
        output = subprocess.check_output(
            ["netsh", "advfirewall", "show", "allprofiles"],
            creationflags=subprocess.CREATE_NO_WINDOW,
        ).decode("utf-8", errors="ignore")
        return {"status": "enabled" if "ON" in output else "disabled"}
    except Exception:
        return {"status": "unknown"}


def add_firewall_rule(
    name: str,
    direction: str,
    action: str,
    port: int | None = None,
    program: str | None = None,
) -> bool:
    config = get_config()
    if config.get("safeguards", True):
        if (
            action.lower() == "allow"
            and direction.lower() == "in"
            and str(port) in ("445", "3389", "22")
        ):
            raise ValueError(f"Safeguard blocked allowing inbound port {port}")
    cmd = [
        "netsh",
        "advfirewall",
        "firewall",
        "add",
        "rule",
        f"name={name}",
        f"dir={direction}",
        f"action={action}",
    ]
    if port:
        cmd.extend(["protocol=TCP", f"localport={port}"])
    if program:
        cmd.append(f"program={program}")
    try:
        subprocess.check_call(cmd, creationflags=subprocess.CREATE_NO_WINDOW)
        return True
    except Exception:
        return False


def remove_firewall_rule(name: str) -> bool:
    try:
        subprocess.check_call(
            ["netsh", "advfirewall", "firewall", "delete", "rule", f"name={name}"],
            creationflags=subprocess.CREATE_NO_WINDOW,
        )
        return True
    except Exception:
        return False


def flush_dns() -> bool:
    try:
        subprocess.check_call(
            ["ipconfig", "/flushdns"], creationflags=subprocess.CREATE_NO_WINDOW
        )
        return True
    except Exception:
        return False

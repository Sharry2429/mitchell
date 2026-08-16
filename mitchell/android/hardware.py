import io
import logging
import subprocess

from PIL import Image

from mitchell.android import adb
from mitchell.core.audit import log_action
from mitchell.core.errors import DeviceOffline, PermissionDenied, SystemMCPError
from mitchell.core.result import MCPResult

"\nAndroid audio management via ADB.\n"


def get_volume() -> MCPResult:
    """Gets the current media volume."""
    log_action("audio", "get_volume", {}, {})
    try:
        result = adb.shell(["media", "volume", "--show"])
        return MCPResult.success(result)
    except Exception as e:
        return MCPResult.fail(str(e))


def set_volume(level: int) -> MCPResult:
    """Sets the media volume to a specific level."""
    log_action("audio", "set_volume", {"level": level}, {})
    try:
        adb.shell(["media", "volume", "--set", str(level)])
        return MCPResult.success(True)
    except Exception as e:
        return MCPResult.fail(str(e))


def mute() -> MCPResult:
    """Mutes the media volume."""
    return set_volume(0)


def unmute(level: int = 5) -> MCPResult:
    """Unmutes the media volume (sets to a default of 5)."""
    return set_volume(level)


"\nAndroid network management via ADB.\n"


def wifi_status() -> MCPResult:
    """Checks if Wi-Fi is enabled."""
    log_action("network", "wifi_status", {}, {})
    try:
        result = adb.shell(["dumpsys", "wifi"])
        if "Wi-Fi is disabled" in result.stdout:
            return MCPResult.success("Disabled")
        return MCPResult.success("Enabled")
    except SystemMCPError as e:
        return MCPResult.fail(str(e))


def ip_addresses() -> MCPResult:
    """Gets IP addresses."""
    log_action("network", "ip_addresses", {}, {})
    try:
        result = adb.shell(["ip", "addr", "show"])
        return MCPResult.success(result.stdout)
    except SystemMCPError as e:
        return MCPResult.fail(str(e))


def ping(host: str, count: int = 4) -> MCPResult:
    """Pings a host from the device."""
    log_action("network", "ping", {"host": host, "count": count}, {})
    try:
        result = adb.shell(["ping", "-c", str(count), host])
        return MCPResult.success(result.stdout)
    except SystemMCPError as e:
        return MCPResult.fail(str(e))


def toggle_airplane_mode(enable: bool) -> MCPResult:
    """Toggles airplane mode."""
    log_action("network", "toggle_airplane_mode", {"enable": enable}, {})
    state = "1" if enable else "0"
    try:
        res = adb.shell(["settings", "put", "global", "airplane_mode_on", state])
        if "Permission denied" in res.stderr:
            return MCPResult.fail(
                "Missing WRITE_SECURE_SETTINGS or ROOT to toggle airplane mode"
            )
        adb.shell(
            [
                "am",
                "broadcast",
                "-a",
                "android.intent.action.AIRPLANE_MODE",
                "--ez",
                "state",
                "true" if enable else "false",
            ]
        )
        return MCPResult.success(True)
    except SystemMCPError as e:
        return MCPResult.fail(str(e))


def get_ssid() -> MCPResult:
    """Gets the connected Wi-Fi SSID."""
    log_action("network", "get_ssid", {}, {})
    try:
        result = adb.shell(["dumpsys", "wifi"])
        for line in result.stdout.splitlines():
            if "mNetworkInfo" in line and "SSID" in line:
                return MCPResult.success(line.strip())
        return MCPResult.success("Unknown")
    except SystemMCPError as e:
        return MCPResult.fail(str(e))


logger = logging.getLogger(__name__)


def toggle_wireless_debugging(enable: bool, device_serial: str | None = None):
    """Toggle wireless debugging on or off."""
    value = "1" if enable else "0"
    cmd = ["adb"]
    if device_serial:
        cmd.extend(["-s", device_serial])
    cmd.extend(["shell", "settings", "put", "global", "adb_wifi_enabled", value])
    try:
        logger.info(f"Setting adb_wifi_enabled to {value}...")
        subprocess.run(cmd, capture_output=True, text=True, check=True)
        logger.info("Wireless debugging toggled successfully.")
    except subprocess.CalledProcessError as e:
        logger.error(f"Failed to toggle wireless debugging: {e.stderr}")
        if "device offline" in e.stderr.lower():
            raise DeviceOffline("Device is offline")
        if "permission denied" in e.stderr.lower():
            raise PermissionDenied("Permission denied toggling adb_wifi_enabled")
        raise


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="WiFi Pairing Automator")
    parser.add_argument(
        "--enable", action="store_true", help="Enable wireless debugging"
    )
    parser.add_argument(
        "--disable", action="store_true", help="Disable wireless debugging"
    )
    parser.add_argument("-s", "--serial", help="Device serial number")
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO)
    if args.enable:
        toggle_wireless_debugging(True, args.serial)
    elif args.disable:
        toggle_wireless_debugging(False, args.serial)
    else:
        logger.warning("Please specify --enable or --disable")
"\nAndroid screen streaming / frame grabbing.\nUses adb exec-out screencap.\n"


def grab_frame():
    """Grabs a single frame from the device screen using adb screencap."""
    try:
        from mitchell.android.connection import get_adb_prefix

        prefix = get_adb_prefix()
        log_action("screen_stream", "grab_frame", {}, {})

        result = subprocess.run(
            prefix + ["exec-out", "screencap", "-p"], capture_output=True, timeout=60
        )
        if result.returncode != 0:
            return MCPResult.fail(
                f"screencap failed: {result.stderr.decode('utf-8', errors='ignore')}"
            )

        output = result.stdout
        if not output:
            return MCPResult.fail("No output received from screen capture")

        img = Image.open(io.BytesIO(output))
        return MCPResult.success(img)
    except subprocess.TimeoutExpired:
        return MCPResult.fail("Failed to grab frame: ADB command timed out after 60s")
    except Exception as e:
        return MCPResult.fail(f"Failed to grab frame: {e}")

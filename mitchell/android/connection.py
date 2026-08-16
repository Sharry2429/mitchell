"""
mitchell.android.connection
Provides access to the active Android device for ADB and uiautomator2.
"""

import json
import os
import subprocess

import uiautomator2 as u2

from mitchell.core.errors import DeviceOffline, SystemMCPError

_active_serial = None
_u2_device = None
_config_path = os.path.expanduser("~/.mitchell_adb_wifi.json")


def _get_saved_wifi_ip() -> str | None:
    if os.path.exists(_config_path):
        try:
            with open(_config_path, "r") as f:
                return json.load(f).get("wifi_ip")
        except (OSError, json.JSONDecodeError):
            pass
    return None


def _save_wifi_ip(ip: str):
    try:
        with open(_config_path, "w") as f:
            json.dump({"wifi_ip": ip}, f)
    except OSError:
        pass




def get_active_serial() -> str:
    """Returns the serial of the active connected device, or raises DeviceOffline."""
    global _active_serial
    if _active_serial:
        # Liveness check
        res = subprocess.run(
            ["adb", "-s", _active_serial, "get-state"], capture_output=True, text=True
        )
        if "device" in res.stdout:
            return _active_serial
        else:
            _active_serial = None

    if not _active_serial:
        result = subprocess.run(["adb", "devices"], capture_output=True, text=True)
        lines = result.stdout.strip().split("\n")[1:]
        devices = [
            line.split("\t")[0]
            for line in lines
            if "device" in line and "offline" not in line
        ]



        if not devices:
            # Fallback to saved Wi-Fi IP
            saved_ip = _get_saved_wifi_ip()
            if saved_ip:
                target = f"{saved_ip}:5555"
                subprocess.run(["adb", "connect", target], capture_output=True)

                # Check again
                result = subprocess.run(
                    ["adb", "devices"], capture_output=True, text=True
                )
                lines = result.stdout.strip().split("\n")[1:]
                devices = [
                    line.split("\t")[0]
                    for line in lines
                    if "device" in line and "offline" not in line
                ]

            if not devices:
                raise DeviceOffline(
                    "No Android devices found or device is offline. Plug in via USB once to enable Auto-Wi-Fi, or check network."
                )

        _active_serial = devices[0]

        # Auto-Upgrade to Wi-Fi ADB if connected via USB
        if ":" not in _active_serial and not _active_serial.startswith("emulator-"):
            try:
                # 1. Get device IP address
                ip_res = subprocess.run(
                    ["adb", "-s", _active_serial, "shell", "ip", "route"],
                    capture_output=True,
                    text=True,
                )
                # Find the wlan0 IP (e.g. 192.168.1.55)
                wifi_ip = None
                for line in ip_res.stdout.split("\n"):
                    if "wlan0" in line and "src" in line:
                        parts = line.split(" ")
                        if "src" in parts:
                            wifi_ip = parts[parts.index("src") + 1]
                            break

                if wifi_ip:
                    # 2. Enable TCP/IP on port 5555
                    subprocess.run(
                        ["adb", "-s", _active_serial, "tcpip", "5555"],
                        capture_output=True,
                        timeout=5,
                    )

                    # 3. Connect wirelessly
                    target = f"{wifi_ip}:5555"
                    connect_res = subprocess.run(
                        ["adb", "connect", target],
                        capture_output=True,
                        text=True,
                        timeout=10,
                    )

                    if "connected" in connect_res.stdout.lower():
                        _active_serial = target
                        _save_wifi_ip(wifi_ip)
            except Exception:
                pass  # Fail gracefully and continue using USB

    return _active_serial


import logging
import time


def ensure_connected(retry_seconds: int = 1, max_wait: int = 2) -> str:
    """Watchdog wrapper around get_active_serial that retries on DeviceOffline."""
    start_time = time.time()
    while True:
        try:
            return get_active_serial()
        except DeviceOffline as e:
            if time.time() - start_time >= max_wait:
                logging.error(f"Device still offline after {max_wait}s. Failing.")
                raise e
            logging.warning(f"Device offline. Retrying in {retry_seconds}s... ({e})")
            time.sleep(retry_seconds)


def get_adb_prefix() -> list[str]:
    """Returns the base adb command list targeting the active device."""
    serial = ensure_connected()
    return ["adb", "-s", serial]


def get_u2_device() -> u2.Device:
    """Returns the active uiautomator2 device connection."""
    global _u2_device
    if _u2_device:
        return _u2_device

    serial = ensure_connected()
    try:
        _u2_device = u2.connect(serial)
        return _u2_device
    except Exception as e:
        raise SystemMCPError(f"Failed to initialize uiautomator2 on {serial}: {e}")


def reset_connection():
    global _active_serial, _u2_device
    _active_serial = None
    _u2_device = None

"""ADB client with automated USB-to-Wireless pairing, discovery, and health checks."""

import re
import shutil
import subprocess
from typing import Any, Dict, List, Optional, Tuple

from mitchell.core.event_log import event_log
from mitchell.core.logging import logger
from mitchell.android.registry import AndroidDevice, device_registry


class ADBClient:
    """Interface for Android Debug Bridge (ADB) operations."""

    def __init__(self, adb_path: Optional[str] = None) -> None:
        self.adb_path = adb_path or shutil.which("adb") or "adb"

    def is_adb_installed(self) -> bool:
        """Check if adb binary is available in PATH."""
        return shutil.which(self.adb_path) is not None

    def run_cmd(self, args: List[str], timeout: int = 15) -> Tuple[int, str, str]:
        """Execute an ADB command."""
        cmd = [self.adb_path] + args
        try:
            res = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=timeout,
                encoding="utf-8",
                errors="replace",
            )
            return res.returncode, res.stdout.strip(), res.stderr.strip()
        except FileNotFoundError:
            return 127, "", "adb command not found in PATH"
        except subprocess.TimeoutExpired:
            return 124, "", f"Command '{' '.join(cmd)}' timed out after {timeout}s"
        except Exception as e:
            return 1, "", str(e)

    def detect_connected_devices(self) -> List[Dict[str, str]]:
        """Query currently connected devices via `adb devices -l`."""
        code, stdout, stderr = self.run_cmd(["devices", "-l"])
        if code != 0:
            logger.warning("ADB detection failed: {}", stderr)
            return []

        devices: List[Dict[str, str]] = []
        for line in stdout.splitlines()[1:]:
            line = line.strip()
            if not line:
                continue
            parts = line.split()
            if len(parts) >= 2:
                serial = parts[0]
                state = parts[1]

                # Extract model / product metadata
                model_match = re.search(r"model:(\S+)", line)
                device_match = re.search(r"device:(\S+)", line)
                model = model_match.group(1) if model_match else (device_match.group(1) if device_match else "Android")

                is_ip = ":" in serial
                devices.append({
                    "serial": serial,
                    "state": state,
                    "model": model,
                    "is_wireless": is_ip,
                })

        return devices

    def extract_device_ip(self, serial: str) -> Optional[str]:
        """Extract Wi-Fi IP address from a connected device."""
        # Method 1: ip route
        code, out, _ = self.run_cmd(["-s", serial, "shell", "ip route"])
        if code == 0:
            for line in out.splitlines():
                if "wlan0" in line and "src" in line:
                    match = re.search(r"src\s+(\d+\.\d+\.\d+\.\d+)", line)
                    if match:
                        return match.group(1)

        # Method 2: ifconfig wlan0 or ip addr show wlan0
        code, out, _ = self.run_cmd(["-s", serial, "shell", "ip addr show wlan0"])
        if code == 0:
            match = re.search(r"inet\s+(\d+\.\d+\.\d+\.\d+)", out)
            if match:
                return match.group(1)

        # Method 3: getprop dhcp.wlan0.ipaddress
        code, out, _ = self.run_cmd(["-s", serial, "shell", "getprop", "dhcp.wlan0.ipaddress"])
        if code == 0 and out.strip():
            return out.strip()

        return None

    def setup_wireless(self, usb_serial: Optional[str] = None, port: int = 5555) -> Dict[str, Any]:
        """
        One-Time USB → Wireless ADB pairing workflow:
        1. Discover USB device
        2. Extract IP address
        3. Switch ADB to TCP/IP mode on port
        4. Connect wirelessly via `adb connect IP:port`
        5. Save in Device Registry
        """
        devices = self.detect_connected_devices()
        usb_devices = [d for d in devices if not d["is_wireless"] and d["state"] == "device"]

        if not usb_devices:
            if not devices:
                return {
                    "success": False,
                    "error": "No Android device detected. Please connect phone via USB with USB Debugging enabled.",
                }
            # Check if already connected wirelessly
            wireless_devices = [d for d in devices if d["is_wireless"] and d["state"] == "device"]
            if wireless_devices:
                w_serial = wireless_devices[0]["serial"]
                return {
                    "success": True,
                    "message": f"Already connected wirelessly to {w_serial}",
                    "wireless_serial": w_serial,
                }
            return {"success": False, "error": "Device found but not in ready state. Check authorization prompt on phone."}

        target_usb = usb_serial or usb_devices[0]["serial"]
        model = next((d["model"] for d in usb_devices if d["serial"] == target_usb), "Android")

        logger.info("Found USB device '{}' ({}). Starting Wireless setup...", target_usb, model)

        # 1. Extract IP
        ip = self.extract_device_ip(target_usb)
        if not ip:
            return {
                "success": False,
                "error": f"Could not determine Wi-Fi IP address for device '{target_usb}'. Make sure Wi-Fi is enabled on phone.",
            }

        # 2. Enable TCP/IP mode
        logger.info("Setting TCP/IP port {} on device '{}'...", port, target_usb)
        code, out, err = self.run_cmd(["-s", target_usb, "tcpip", str(port)])
        if code != 0:
            return {"success": False, "error": f"Failed to switch to tcpip mode: {err}"}

        # 3. Connect wirelessly
        target_endpoint = f"{ip}:{port}"
        logger.info("Connecting to wireless endpoint '{}'...", target_endpoint)
        code, out, err = self.run_cmd(["connect", target_endpoint])
        if "connected" not in out.lower():
            return {"success": False, "error": f"Failed to connect to {target_endpoint}: {out or err}"}

        # 4. Register in DeviceRegistry
        dev = AndroidDevice(
            serial=target_endpoint,
            usb_serial=target_usb,
            ip_address=ip,
            port=port,
            friendly_name=f"{model} (Wireless)",
            model=model,
            status="online",
            is_wireless=True,
        )
        device_registry.register(dev)

        event_log.log_event(
            "android_wireless_paired",
            source="adb_client",
            data={"serial": target_endpoint, "usb_serial": target_usb, "ip": ip, "model": model},
        )

        return {
            "success": True,
            "message": f"Wireless ADB established! You can now safely unplug the USB cable.",
            "wireless_serial": target_endpoint,
            "device": dev.model_dump(),
        }

    def check_device_health(self, serial: str) -> bool:
        """Check if device is responsive."""
        code, out, _ = self.run_cmd(["-s", serial, "get-state"], timeout=5)
        is_healthy = code == 0 and out.strip() == "device"
        device_registry.update_status(serial, "online" if is_healthy else "offline")
        return is_healthy


adb_client = ADBClient()

__all__ = ["ADBClient", "adb_client"]

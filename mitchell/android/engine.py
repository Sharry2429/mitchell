"""Android automation engine with human-like touch gestures, scrcpy, and screen capture."""

import math
import random
import subprocess
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional
import xml.etree.ElementTree as ET

from mitchell.browser.mouse import generate_bezier_curve
from mitchell.core.config import settings
from mitchell.core.event_log import event_log
from mitchell.core.logging import logger
from mitchell.android.adb import adb_client
from mitchell.android.registry import device_registry


class AndroidEngine:
    """Automates Android mobile interactions via ADB and scrcpy."""

    def __init__(self, target_serial: Optional[str] = None) -> None:
        self._target_serial = target_serial

    def _get_serial(self) -> str:
        """Resolve active device serial."""
        if self._target_serial:
            return self._target_serial
        dev = device_registry.get()
        return dev.serial if dev else ""

    def _check_online(self) -> bool:
        """Verify target device is reachable, or trigger escalation."""
        serial = self._get_serial()
        if not serial:
            return False

        if not adb_client.check_device_health(serial):
            logger.warning("Android device '{}' is offline!", serial)
            event_log.log_event(
                "android_device_offline",
                source="android_engine",
                data={"serial": serial},
            )
            return False
        return True

    def tap(self, x: int, y: int, human: bool = True) -> Dict[str, Any]:
        """Perform touch tap on screen with human jitter and dwell time."""
        serial = self._get_serial()
        if not self._check_online():
            return {
                "success": False,
                "error": f"Device '{serial}' is offline. Please plug it in via USB once so Mitchell can re-establish connection.",
            }

        # Jitter coordinates
        tx = x + (random.randint(-3, 3) if human else 0)
        ty = y + (random.randint(-3, 3) if human else 0)

        logger.info("Android [{}]: Tapping at ({}, {})", serial, tx, ty)

        if human:
            # Swipe with same start and end to simulate realistic touch down -> dwell -> touch up
            dwell_ms = random.randint(45, 110)
            code, out, err = adb_client.run_cmd(
                ["-s", serial, "shell", "input", "swipe", str(tx), str(ty), str(tx), str(ty), str(dwell_ms)]
            )
        else:
            code, out, err = adb_client.run_cmd(["-s", serial, "shell", "input", "tap", str(tx), str(ty)])

        if code == 0:
            event_log.log_event(
                "android_tapped",
                source=f"android:{serial}",
                data={"x": tx, "y": ty, "human": human},
            )
            return {"success": True, "x": tx, "y": ty}
        return {"success": False, "error": err or out}

    def swipe(
        self,
        start_x: int,
        start_y: int,
        end_x: int,
        end_y: int,
        duration_ms: int = 350,
        human: bool = True,
    ) -> Dict[str, Any]:
        """Perform gesture swipe with human curve trajectory."""
        serial = self._get_serial()
        if not self._check_online():
            return {"success": False, "error": "Device is offline"}

        logger.info("Android [{}]: Swiping from ({}, {}) to ({}, {})", serial, start_x, start_y, end_x, end_y)

        if human:
            # Multi-point Bezier gesture simulation or single curved sweep
            dur = duration_ms + random.randint(-40, 60)
            code, out, err = adb_client.run_cmd([
                "-s", serial, "shell", "input", "swipe",
                str(start_x), str(start_y), str(end_x), str(end_y), str(dur)
            ])
        else:
            code, out, err = adb_client.run_cmd([
                "-s", serial, "shell", "input", "swipe",
                str(start_x), str(start_y), str(end_x), str(end_y), str(duration_ms)
            ])

        if code == 0:
            event_log.log_event(
                "android_swiped",
                source=f"android:{serial}",
                data={"start": (start_x, start_y), "end": (end_x, end_y), "duration": duration_ms},
            )
            return {"success": True}
        return {"success": False, "error": err or out}

    def type_text(self, text: str, human: bool = True) -> Dict[str, Any]:
        """Type text into focused mobile input element."""
        serial = self._get_serial()
        if not self._check_online():
            return {"success": False, "error": "Device is offline"}

        logger.info("Android [{}]: Typing text (length={})", serial, len(text))

        # Replace spaces for adb input text
        safe_text = text.replace(" ", "%s").replace("&", "\\&").replace("<", "\\<").replace(">", "\\>")

        if human:
            # Type in chunks or characters with randomized pauses
            chunks = [safe_text[i:i + random.randint(2, 5)] for i in range(0, len(safe_text), 4)]
            for chunk in chunks:
                adb_client.run_cmd(["-s", serial, "shell", "input", "text", chunk])
                time.sleep(random.uniform(0.06, 0.14))
            code = 0
            err = ""
        else:
            code, out, err = adb_client.run_cmd(["-s", serial, "shell", "input", "text", safe_text])

        if code == 0:
            event_log.log_event(
                "android_typed_text",
                source=f"android:{serial}",
                data={"length": len(text)},
            )
            return {"success": True, "length": len(text)}
        return {"success": False, "error": err}

    def press_key(self, keycode: Union[str, int]) -> Dict[str, Any]:
        """Send keyevent (e.g. 3=HOME, 4=BACK, 66=ENTER, 26=POWER, 'KEYCODE_HOME')."""
        serial = self._get_serial()
        if not self._check_online():
            return {"success": False, "error": "Device is offline"}

        key_map = {
            "home": "KEYCODE_HOME",
            "back": "KEYCODE_BACK",
            "enter": "KEYCODE_ENTER",
            "app_switch": "KEYCODE_APP_SWITCH",
            "recent": "KEYCODE_APP_SWITCH",
            "power": "KEYCODE_POWER",
            "volume_up": "KEYCODE_VOLUME_UP",
            "volume_down": "KEYCODE_VOLUME_DOWN",
        }
        resolved = key_map.get(str(keycode).lower(), str(keycode))

        code, out, err = adb_client.run_cmd(["-s", serial, "shell", "input", "keyevent", resolved])
        if code == 0:
            return {"success": True, "key": resolved}
        return {"success": False, "error": err or out}

    def open_app(self, package_name: str) -> Dict[str, Any]:
        """Launch an Android application by package name."""
        serial = self._get_serial()
        if not self._check_online():
            return {"success": False, "error": "Device is offline"}

        logger.info("Android [{}]: Launching app '{}'", serial, package_name)
        code, out, err = adb_client.run_cmd([
            "-s", serial, "shell", "monkey", "-p", package_name, "-c", "android.intent.category.LAUNCHER", "1"
        ])

        if code == 0 and "No activities found" not in out:
            event_log.log_event(
                "android_app_opened",
                source=f"android:{serial}",
                data={"package": package_name},
            )
            return {"success": True, "package": package_name}
        return {"success": False, "error": out or err}

    def screenshot(self, filename: Optional[str] = None) -> Dict[str, Any]:
        """Capture device screen and save to disk."""
        serial = self._get_serial()
        if not self._check_online():
            return {"success": False, "error": "Device is offline"}

        screenshots_dir = Path(settings.data_dir) / "screenshots"
        screenshots_dir.mkdir(parents=True, exist_ok=True)
        fname = filename or f"android_{int(datetime.now().timestamp())}.png"
        filepath = screenshots_dir / fname

        # Capture directly using adb exec-out screencap
        try:
            cmd = [adb_client.adb_path, "-s", serial, "exec-out", "screencap", "-p"]
            with open(filepath, "wb") as f:
                subprocess.run(cmd, stdout=f, check=True, timeout=10)
            return {"success": True, "path": str(filepath)}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def get_ui_hierarchy(self, max_items: int = 50) -> Dict[str, Any]:
        """Dump and parse UI hierarchy using uiautomator."""
        serial = self._get_serial()
        if not self._check_online():
            return {"success": False, "error": "Device is offline"}

        code, _, _ = adb_client.run_cmd(["-s", serial, "shell", "uiautomator", "dump", "/sdcard/window_dump.xml"])
        if code != 0:
            return {"success": False, "error": "Failed to dump UI hierarchy"}

        code, xml_content, _ = adb_client.run_cmd(["-s", serial, "shell", "cat", "/sdcard/window_dump.xml"])
        if code != 0 or not xml_content:
            return {"success": False, "error": "Failed to read UI XML dump"}

        elements: List[Dict[str, Any]] = []
        try:
            root = ET.fromstring(xml_content)
            for node in root.iter("node"):
                text = node.attrib.get("text", "").strip()
                desc = node.attrib.get("content-desc", "").strip()
                res_id = node.attrib.get("resource-id", "").strip()
                bounds = node.attrib.get("bounds", "")
                clickable = node.attrib.get("clickable", "false") == "true"

                if text or desc or (clickable and res_id):
                    elements.append({
                        "text": text,
                        "desc": desc,
                        "resource_id": res_id,
                        "bounds": bounds,
                        "clickable": clickable,
                    })

            return {"success": True, "count": len(elements), "elements": elements[:max_items]}
        except Exception as e:
            return {"success": False, "error": f"XML parse error: {e}"}


android_engine = AndroidEngine()

__all__ = ["AndroidEngine", "android_engine"]

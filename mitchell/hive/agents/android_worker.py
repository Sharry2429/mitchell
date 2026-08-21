"""Android Worker Agent executing mobile tasks and wireless pairing in the Hive."""

from typing import Any, Dict, Optional, Union
from mitchell.core.event_log import event_log
from mitchell.core.logging import logger
from mitchell.android.adb import adb_client
from mitchell.android.engine import AndroidEngine, android_engine
from mitchell.android.registry import device_registry
from mitchell.hive.agents.base import BaseAgent


class AndroidWorkerAgent(BaseAgent):
    """Hive Agent specializing in Android automation, touch gestures, and wireless connectivity."""

    def __init__(
        self,
        agent_id: str = "android_worker",
        description: str = "Automates Android mobile devices via Wireless ADB and touch gestures",
        engine: Optional[AndroidEngine] = None,
    ) -> None:
        super().__init__(agent_id=agent_id, description=description)
        self.engine = engine or android_engine

    def process(self, message: Union[str, Dict[str, Any]], sender: str = "manager") -> Dict[str, Any]:
        """Process Android mobile automation task."""
        logger.info("AndroidWorker received task from {}: {}", sender, message)

        action_data = self._parse_payload(message)
        action = action_data.get("action", "").lower()

        event_log.log_event(
            "android_worker_task_started",
            source=self.agent_id,
            data={"sender": sender, "action": action, "payload": action_data},
        )

        try:
            if action in ("setup", "setup_wireless", "pair"):
                res = adb_client.setup_wireless(
                    usb_serial=action_data.get("usb_serial"),
                    port=action_data.get("port", 5555),
                )
                return {"status": "success" if res.get("success") else "error", "result": res}

            elif action in ("tap", "click"):
                x = int(action_data.get("x", 0))
                y = int(action_data.get("y", 0))
                res = self.engine.tap(x, y, human=action_data.get("human", True))
                return {"status": "success" if res.get("success") else "error", "result": res}

            elif action == "swipe":
                res = self.engine.swipe(
                    start_x=int(action_data.get("x1", 0)),
                    start_y=int(action_data.get("y1", 0)),
                    end_x=int(action_data.get("x2", 0)),
                    end_y=int(action_data.get("y2", 0)),
                    duration_ms=int(action_data.get("duration", 350)),
                    human=action_data.get("human", True),
                )
                return {"status": "success" if res.get("success") else "error", "result": res}

            elif action in ("type", "input"):
                text = action_data.get("text", "")
                res = self.engine.type_text(text, human=action_data.get("human", True))
                return {"status": "success" if res.get("success") else "error", "result": res}

            elif action in ("key", "press_key"):
                key = action_data.get("key") or action_data.get("target") or "HOME"
                res = self.engine.press_key(key)
                return {"status": "success" if res.get("success") else "error", "result": res}

            elif action in ("open", "launch", "open_app"):
                pkg = action_data.get("package") or action_data.get("target")
                if not pkg:
                    return {"status": "error", "message": "Missing 'package' parameter"}
                res = self.engine.open_app(pkg)
                return {"status": "success" if res.get("success") else "error", "result": res}

            elif action in ("screenshot", "screencap"):
                res = self.engine.screenshot(filename=action_data.get("filename"))
                return {"status": "success" if res.get("success") else "error", "result": res}

            elif action in ("hierarchy", "dump"):
                res = self.engine.get_ui_hierarchy()
                return {"status": "success" if res.get("success") else "error", "result": res}

            elif action in ("devices", "list_devices"):
                devices = [d.model_dump() for d in device_registry.list_all()]
                connected = adb_client.detect_connected_devices()
                return {"status": "success", "registered_devices": devices, "active_adb_devices": connected}

            else:
                return {
                    "status": "error",
                    "message": f"Unknown Android action '{action}'",
                    "supported_actions": [
                        "setup_wireless", "tap", "swipe", "type", "key", "open", "screenshot", "hierarchy", "list_devices"
                    ],
                }

        except Exception as exc:
            logger.error("AndroidWorker execution error: {}", exc)
            event_log.log_event(
                "android_worker_error",
                source=self.agent_id,
                data={"error": str(exc)},
            )
            return {"status": "error", "error": str(exc)}

    def _parse_payload(self, message: Union[str, Dict[str, Any]]) -> Dict[str, Any]:
        """Parse string or dict into structured Android task data."""
        if isinstance(message, dict):
            return message

        text = str(message).strip()
        parts = text.split()
        first_word = parts[0].lower() if parts else ""

        if first_word in ("setup", "pair", "wireless"):
            return {"action": "setup_wireless"}
        elif first_word in ("tap", "click") and len(parts) >= 3:
            return {"action": "tap", "x": int(parts[1]), "y": int(parts[2])}
        elif first_word == "swipe" and len(parts) >= 5:
            return {"action": "swipe", "x1": int(parts[1]), "y1": int(parts[2]), "x2": int(parts[3]), "y2": int(parts[4])}
        elif first_word == "type" and len(parts) >= 2:
            return {"action": "type", "text": " ".join(parts[1:])}
        elif first_word in ("key", "press") and len(parts) >= 2:
            return {"action": "key", "key": parts[1]}
        elif first_word in ("open", "launch") and len(parts) >= 2:
            return {"action": "open", "package": parts[1]}
        elif first_word in ("screenshot", "screencap"):
            return {"action": "screenshot"}
        elif first_word in ("hierarchy", "dump"):
            return {"action": "hierarchy"}
        elif first_word in ("devices", "list_devices"):
            return {"action": "list_devices"}

        return {"action": "raw", "content": text}


__all__ = ["AndroidWorkerAgent"]

"""Windows Worker Agent executing desktop and UI automation tasks in the Hive."""

from typing import Any, Dict, Optional, Union
from mitchell.core.event_log import event_log
from mitchell.core.logging import logger
from mitchell.hive.agents.base import BaseAgent
from mitchell.windows.engine import WindowsEngine, windows_engine


class WindowsWorkerAgent(BaseAgent):
    """Hive Agent specializing in native Windows desktop applications and UI automation."""

    def __init__(
        self,
        agent_id: str = "windows_worker",
        description: str = "Automates native Windows apps, window management, and UIA elements",
        engine: Optional[WindowsEngine] = None,
    ) -> None:
        super().__init__(agent_id=agent_id, description=description)
        self.engine = engine or windows_engine

    def process(self, message: Union[str, Dict[str, Any]], sender: str = "manager") -> Dict[str, Any]:
        """Process Windows desktop automation task."""
        logger.info("WindowsWorker received task from {}: {}", sender, message)

        action_data = self._parse_payload(message)
        action = action_data.get("action", "").lower()

        event_log.log_event(
            "windows_worker_task_started",
            source=self.agent_id,
            data={"sender": sender, "action": action, "payload": action_data},
        )

        try:
            if action in ("launch", "start", "open"):
                cmd = action_data.get("cmd") or action_data.get("target") or action_data.get("path")
                if not cmd:
                    return {"status": "error", "message": "Missing 'cmd' parameter"}
                res = self.engine.launch_app(cmd)
                return {"status": "success" if res.get("success") else "error", "result": res}

            elif action in ("focus", "activate"):
                title = action_data.get("title") or action_data.get("target")
                if not title:
                    return {"status": "error", "message": "Missing 'title' parameter"}
                res = self.engine.focus_window(title)
                return {"status": "success" if res.get("success") else "error", "result": res}

            elif action in ("click", "click_element"):
                res = self.engine.click_element(
                    title_query=action_data.get("title"),
                    name=action_data.get("name") or action_data.get("target"),
                    automation_id=action_data.get("automation_id"),
                    control_type=action_data.get("control_type"),
                    human=action_data.get("human", True),
                )
                return {"status": "success" if res.get("success") else "error", "result": res}

            elif action in ("type", "input"):
                text = action_data.get("text", "")
                res = self.engine.type_text(
                    text=text,
                    title_query=action_data.get("title"),
                    name=action_data.get("name"),
                    human=action_data.get("human", True),
                )
                return {"status": "success" if res.get("success") else "error", "result": res}

            elif action in ("keys", "send_keys"):
                keys_str = action_data.get("keys") or action_data.get("target")
                if not keys_str:
                    return {"status": "error", "message": "Missing 'keys' parameter"}
                res = self.engine.send_keys(keys_str)
                return {"status": "success" if res.get("success") else "error", "result": res}

            elif action in ("inspect", "inspect_tree", "tree"):
                title = action_data.get("title") or action_data.get("target")
                res = self.engine.inspect_tree(title_query=title)
                return {"status": "success" if res.get("success") else "error", "result": res}

            elif action in ("list_windows", "windows"):
                res = self.engine.list_windows()
                return {"status": "success", "count": len(res), "windows": res}

            elif action == "screenshot":
                title = action_data.get("title")
                res = self.engine.screenshot_window(title_query=title)
                return {"status": "success" if res.get("success") else "error", "result": res}

            else:
                return {
                    "status": "error",
                    "message": f"Unknown Windows action '{action}'",
                    "supported_actions": [
                        "launch", "focus", "click", "type", "keys", "inspect", "list_windows", "screenshot"
                    ],
                }

        except Exception as exc:
            logger.error("WindowsWorker execution error: {}", exc)
            event_log.log_event(
                "windows_worker_error",
                source=self.agent_id,
                data={"error": str(exc)},
            )
            return {"status": "error", "error": str(exc)}

    def _parse_payload(self, message: Union[str, Dict[str, Any]]) -> Dict[str, Any]:
        """Parse string or dict into structured Windows task data."""
        if isinstance(message, dict):
            return message

        text = str(message).strip()
        parts = text.split(maxsplit=1)
        first_word = parts[0].lower() if parts else ""
        remainder = parts[1] if len(parts) > 1 else ""

        if first_word in ("launch", "start", "open"):
            return {"action": "launch", "cmd": remainder}
        elif first_word in ("focus", "activate"):
            return {"action": "focus", "title": remainder}
        elif first_word == "click":
            return {"action": "click", "name": remainder}
        elif first_word == "type":
            type_parts = remainder.split(maxsplit=1)
            target = type_parts[0] if len(type_parts) > 1 else ""
            txt = type_parts[1] if len(type_parts) > 1 else remainder
            return {"action": "type", "name": target, "text": txt}
        elif first_word == "keys":
            return {"action": "keys", "keys": remainder}
        elif first_word in ("inspect", "tree"):
            return {"action": "inspect", "title": remainder or None}
        elif first_word in ("list", "windows", "list_windows"):
            return {"action": "list_windows"}
        elif first_word == "screenshot":
            return {"action": "screenshot", "title": remainder or None}

        return {"action": "raw", "content": text}


__all__ = ["WindowsWorkerAgent"]

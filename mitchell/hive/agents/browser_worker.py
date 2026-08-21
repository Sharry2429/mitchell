"""Browser Worker Agent executing web automation tasks in the Hive."""

import asyncio
from typing import Any, Dict, Optional, Union
from mitchell.core.event_log import event_log
from mitchell.core.logging import logger
from mitchell.browser.engine import BrowserEngine
from mitchell.hive.agents.base import BaseAgent


class BrowserWorkerAgent(BaseAgent):
    """Hive Agent specializing in browser navigation and DOM interactions."""

    def __init__(
        self,
        agent_id: str = "browser_worker",
        description: str = "Automates browser workflows using Playwright and human-like interactions",
        session_id: str = "worker_default",
    ) -> None:
        super().__init__(agent_id=agent_id, description=description)
        self.session_id = session_id
        self.engine = BrowserEngine(session_id=self.session_id)

    def process(self, message: Union[str, Dict[str, Any]], sender: str = "manager") -> Dict[str, Any]:
        """Process browser task synchronously via asyncio loop."""
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # In async context: schedule in separate thread or use task
                import concurrent.futures
                with concurrent.futures.ThreadPoolExecutor() as pool:
                    result = pool.submit(asyncio.run, self._async_process(message, sender)).result()
            else:
                result = loop.run_until_complete(self._async_process(message, sender))
        except Exception:
            result = asyncio.run(self._async_process(message, sender))

        return result

    async def _async_process(self, message: Union[str, Dict[str, Any]], sender: str) -> Dict[str, Any]:
        """Execute browser action according to payload."""
        logger.info("BrowserWorker received task from {}: {}", sender, message)

        action_data = self._parse_payload(message)
        action = action_data.get("action", "").lower()

        event_log.log_event(
            "browser_worker_task_started",
            source=self.agent_id,
            data={"sender": sender, "action": action, "payload": action_data},
        )

        try:
            if action in ("goto", "navigate", "open"):
                url = action_data.get("url") or action_data.get("target")
                if not url:
                    return {"status": "error", "message": "Missing 'url' parameter"}
                res = await self.engine.goto(url)
                return {"status": "success", "result": res}

            elif action == "click":
                selector = action_data.get("selector") or action_data.get("target")
                if not selector:
                    return {"status": "error", "message": "Missing 'selector' parameter"}
                res = await self.engine.click(selector, human=action_data.get("human", True))
                return {"status": "success", "result": res}

            elif action in ("type", "fill"):
                selector = action_data.get("selector") or action_data.get("target")
                text = action_data.get("text", "")
                if not selector:
                    return {"status": "error", "message": "Missing 'selector' parameter"}
                res = await self.engine.type_text(selector, text, human=action_data.get("human", True))
                return {"status": "success", "result": res}

            elif action == "snapshot":
                res = await self.engine.snapshot()
                return {"status": "success", "result": res}

            elif action == "screenshot":
                filename = action_data.get("filename")
                res = await self.engine.screenshot(filename=filename)
                return {"status": "success", "result": res}

            elif action == "close":
                res = await self.engine.close()
                return {"status": "success", "result": {"closed": res}}

            else:
                # Default: if string is a URL, navigate to it
                raw_str = str(message).strip()
                if raw_str.startswith("http://") or raw_str.startswith("https://"):
                    res = await self.engine.goto(raw_str)
                    return {"status": "success", "result": res}

                return {
                    "status": "error",
                    "message": f"Unknown browser action '{action}'",
                    "supported_actions": ["goto", "click", "type", "snapshot", "screenshot", "close"],
                }

        except Exception as exc:
            logger.error("BrowserWorker execution error: {}", exc)
            event_log.log_event(
                "browser_worker_error",
                source=self.agent_id,
                data={"error": str(exc)},
            )
            return {"status": "error", "error": str(exc)}

    def _parse_payload(self, message: Union[str, Dict[str, Any]]) -> Dict[str, Any]:
        """Convert string or dictionary message to structured action data."""
        if isinstance(message, dict):
            return message

        text = str(message).strip()
        parts = text.split(maxsplit=1)
        first_word = parts[0].lower() if parts else ""
        remainder = parts[1] if len(parts) > 1 else ""

        if first_word in ("goto", "navigate", "open"):
            return {"action": "goto", "url": remainder}
        elif first_word == "click":
            return {"action": "click", "selector": remainder}
        elif first_word == "type":
            type_parts = remainder.split(maxsplit=1)
            sel = type_parts[0] if type_parts else ""
            txt = type_parts[1] if len(type_parts) > 1 else ""
            return {"action": "type", "selector": sel, "text": txt}
        elif first_word == "snapshot":
            return {"action": "snapshot"}
        elif first_word == "screenshot":
            return {"action": "screenshot", "filename": remainder or None}

        return {"action": "raw", "content": text}


__all__ = ["BrowserWorkerAgent"]

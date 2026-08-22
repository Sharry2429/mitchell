"""Communication Worker Agent executing WhatsApp, SMS, Email, and scheduled messaging in Hive."""

import json
from typing import Any, Dict, Union

from mitchell.comms import (
    call_manager,
    communication_hub,
    message_scheduler,
    sms_manager,
    whatsapp_bridge,
    whatsapp_mcp,
)
from mitchell.core.event_log import event_log
from mitchell.core.logging import logger
from mitchell.hive.agents.base import BaseAgent


class CommsWorkerAgent(BaseAgent):
    """Hive Agent specializing in multi-channel messaging (WhatsApp MCP, SMS, Email, Calls)."""

    def __init__(
        self,
        agent_id: str = "comms_worker",
        description: str = "Handles multi-channel communication via WhatsApp MCP, SMS, phone calls, and email",
    ) -> None:
        super().__init__(agent_id=agent_id, description=description)

    def process(self, message: Union[str, Dict[str, Any]], sender: str = "manager") -> Dict[str, Any]:
        """Process communication task."""
        logger.info("CommsWorker received task from {}: {}", sender, message)

        if isinstance(message, dict):
            action = message.get("action", "")
            data = message
        else:
            text = str(message).strip()
            parts = text.split(maxsplit=1)
            action = parts[0].lower() if parts else ""
            data = {"raw": parts[1]} if len(parts) > 1 else {}

        event_log.log_event(
            "comms_worker_task_started",
            source=self.agent_id,
            data={"action": action, "sender": sender},
        )

        try:
            if action in ("whatsapp", "send_whatsapp"):
                recipient = data.get("recipient") or data.get("phone_number") or ""
                msg_text = data.get("message") or data.get("text") or data.get("raw") or ""
                res = whatsapp_mcp.send_message(recipient=recipient, message=msg_text)
                return {"status": "success", "result": res}

            elif action in ("sms", "send_sms"):
                recipient = data.get("recipient") or data.get("phone_number") or ""
                msg_text = data.get("message") or data.get("text") or data.get("raw") or ""
                res = sms_manager.send_sms(phone_number=recipient, message=msg_text)
                return {"status": "success", "result": res}

            elif action in ("call", "make_call"):
                recipient = data.get("recipient") or data.get("phone_number") or ""
                res = call_manager.make_call(phone_number=recipient)
                return {"status": "success", "result": res}

            elif action in ("inbox", "list_messages"):
                msgs = communication_hub.list_messages(channel=data.get("channel"), limit=10)
                return {"status": "success", "messages": msgs}

            return {"status": "success", "message": f"Comms task processed: {message}"}

        except Exception as e:
            logger.error("CommsWorker error: {}", e)
            return {"status": "error", "error": str(e)}


__all__ = ["CommsWorkerAgent"]

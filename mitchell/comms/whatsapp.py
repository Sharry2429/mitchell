"""WhatsApp Web automation and message bridge for Mitchell with whatsapp-mcp support."""

import urllib.parse
from typing import Any, Dict, Optional

from mitchell.comms.hub import communication_hub
from mitchell.comms.whatsapp_mcp import whatsapp_mcp
from mitchell.core.event_log import event_log
from mitchell.core.logging import logger


class WhatsAppBridge:
    """Automates WhatsApp messaging via WhatsApp MCP (https://github.com/lharries/whatsapp-mcp) or Web intent."""

    def send_whatsapp_message(self, phone_number: str, text: str, use_mcp: bool = True) -> Dict[str, Any]:
        """Send a WhatsApp message via WhatsApp MCP or WhatsApp Web direct URL intent."""
        if use_mcp:
            return whatsapp_mcp.send_message(recipient=phone_number, message=text)

        clean_number = "".join(c for c in phone_number if c.isdigit())
        encoded_text = urllib.parse.quote(text)
        wa_url = f"https://web.whatsapp.com/send?phone={clean_number}&text={encoded_text}"

        # Record in unified hub
        communication_hub.record_message(
            channel="whatsapp",
            sender="me",
            recipient=clean_number,
            content=text,
            is_incoming=False,
            metadata={"url": wa_url},
        )

        # Trigger in browser or launch
        import subprocess
        try:
            subprocess.Popen(f'start {wa_url}', shell=True)
            return {"status": "success", "recipient": clean_number, "action": "opened_web_chat"}
        except Exception as e:
            return {"status": "error", "message": str(e)}


whatsapp_bridge = WhatsAppBridge()

__all__ = ["WhatsAppBridge", "whatsapp_bridge"]

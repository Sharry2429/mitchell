"""Unified Communication Hub aggregating WhatsApp, SMS, Phone calls, Email, and scheduled messages."""

import json
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Literal, Optional
from pydantic import BaseModel, Field

from mitchell.core.event_log import event_log
from mitchell.core.logging import logger
from mitchell.workspace.storage import workspace_storage


class UnifiedMessage(BaseModel):
    """Normalized message representation across WhatsApp, SMS, Email, and internal channels."""

    id: str = Field(default_factory=lambda: f"msg_{str(uuid.uuid4())[:8]}")
    channel: Literal["whatsapp", "sms", "email", "local", "system"]
    sender: str
    recipient: str
    content: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    is_read: bool = False
    is_incoming: bool = True
    metadata: Dict[str, Any] = Field(default_factory=dict)


class CommunicationHub:
    """Unified communications manager in Studio."""

    def __init__(self) -> None:
        self.storage = workspace_storage
        self._hub_file = "messages/hub_messages.json"
        self._messages: List[UnifiedMessage] = []
        self._load_messages()

    def _load_messages(self) -> None:
        """Load stored unified messages."""
        try:
            content = self.storage.read_file(self._hub_file)
            data = json.loads(content)
            self._messages = [UnifiedMessage.model_validate(m) for m in data]
        except Exception:
            self._messages = []

    def _save_messages(self) -> None:
        """Persist message store."""
        dumpable = [m.model_dump(mode="json") for m in self._messages]
        self.storage.write_file(
            rel_path=self._hub_file,
            content=json.dumps(dumpable, indent=2),
            file_type="message",
            change_summary="Communication Hub update",
        )

    def record_message(
        self,
        channel: Literal["whatsapp", "sms", "email", "local", "system"],
        sender: str,
        recipient: str,
        content: str,
        is_incoming: bool = True,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> UnifiedMessage:
        """Record an incoming or outgoing message into the unified hub."""
        msg = UnifiedMessage(
            channel=channel,
            sender=sender,
            recipient=recipient,
            content=content,
            is_incoming=is_incoming,
            metadata=metadata or {},
        )
        self._messages.append(msg)
        self._save_messages()

        event_log.log_event(
            "communication_message_recorded",
            source="comms_hub",
            data={"channel": channel, "sender": sender, "recipient": recipient},
        )
        logger.info("Comms Hub: [{}] Message between '{}' and '{}'", channel, sender, recipient)
        return msg

    def list_messages(
        self,
        channel: Optional[str] = None,
        contact: Optional[str] = None,
        limit: int = 50,
    ) -> List[Dict[str, Any]]:
        """List unified inbox messages with optional channel and contact filtering."""
        filtered = self._messages
        if channel:
            filtered = [m for m in filtered if m.channel == channel]
        if contact:
            c = contact.lower()
            filtered = [m for m in filtered if c in m.sender.lower() or c in m.recipient.lower()]

        sorted_msgs = sorted(filtered, key=lambda x: x.timestamp, reverse=True)[:limit]
        return [m.model_dump(mode="json") for m in sorted_msgs]

    def search_all_channels(self, query: str) -> List[Dict[str, Any]]:
        """Search all messages across WhatsApp, SMS, and Email."""
        q = query.lower()
        matches = [
            m for m in self._messages
            if q in m.content.lower() or q in m.sender.lower() or q in m.recipient.lower()
        ]
        return [m.model_dump(mode="json") for m in sorted(matches, key=lambda x: x.timestamp, reverse=True)]


communication_hub = CommunicationHub()

__all__ = ["UnifiedMessage", "CommunicationHub", "communication_hub"]

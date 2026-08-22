"""Scheduled and delayed message sending queue."""

import time
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Literal, Optional
from pydantic import BaseModel, Field

from mitchell.comms.hub import communication_hub
from mitchell.core.event_log import event_log
from mitchell.core.logging import logger


class ScheduledMessage(BaseModel):
    """A message scheduled to be dispatched at a future timestamp."""

    schedule_id: str = Field(default_factory=lambda: f"sch_{str(uuid.uuid4())[:8]}")
    channel: Literal["whatsapp", "sms", "email"]
    recipient: str
    content: str
    scheduled_for: datetime
    is_dispatched: bool = False
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class MessageScheduler:
    """Queues and executes delayed communications."""

    def __init__(self) -> None:
        self._queue: List[ScheduledMessage] = []

    def schedule_message(
        self,
        channel: Literal["whatsapp", "sms", "email"],
        recipient: str,
        content: str,
        scheduled_for: datetime,
    ) -> ScheduledMessage:
        """Add a message to the dispatch schedule."""
        item = ScheduledMessage(
            channel=channel,
            recipient=recipient,
            content=content,
            scheduled_for=scheduled_for,
        )
        self._queue.append(item)

        event_log.log_event(
            "message_scheduled",
            source="message_scheduler",
            data={"channel": channel, "recipient": recipient, "time": scheduled_for.isoformat()},
        )
        logger.info("Message scheduled for {} via [{}] to '{}'", scheduled_for, channel, recipient)
        return item

    def check_and_dispatch(self) -> List[Dict[str, Any]]:
        """Check for and dispatch any scheduled messages whose time has arrived."""
        now = datetime.now(timezone.utc)
        dispatched = []

        for item in self._queue:
            if not item.is_dispatched and item.scheduled_for <= now:
                # Dispatch
                if item.channel == "whatsapp":
                    from mitchell.comms.whatsapp import whatsapp_bridge
                    whatsapp_bridge.send_whatsapp_message(item.recipient, item.content)
                elif item.channel == "sms":
                    from mitchell.comms.sms import sms_manager
                    sms_manager.send_sms(item.recipient, item.content)
                elif item.channel == "email":
                    from mitchell.workspace.mail import mail_engine
                    mail_engine.compose_draft(item.recipient, "Scheduled Message", item.content)

                item.is_dispatched = True
                dispatched.append(item.model_dump(mode="json"))

        return dispatched

    def list_scheduled(self) -> List[Dict[str, Any]]:
        """List upcoming pending scheduled messages."""
        return [
            m.model_dump(mode="json")
            for m in sorted(self._queue, key=lambda x: x.scheduled_for)
            if not m.is_dispatched
        ]


message_scheduler = MessageScheduler()

__all__ = ["ScheduledMessage", "MessageScheduler", "message_scheduler"]

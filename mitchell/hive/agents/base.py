"""Base Agent definition for the Mitchell Hive."""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional


class BaseAgent:
    """Base class for specialized Hive agents."""

    def __init__(self, agent_id: str, description: str = "") -> None:
        self.agent_id = agent_id
        self.description = description
        self.inbox: List[Dict[str, Any]] = []
        self.outbox: List[Dict[str, Any]] = []

    def receive_message(self, message: Any, sender: str = "manager") -> Any:
        """Receive message into inbox, process it, and record response in outbox."""
        inbox_entry = {
            "sender": sender,
            "content": message,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        self.inbox.append(inbox_entry)

        # Process the message
        response = self.process(message, sender=sender)

        outbox_entry = {
            "recipient": sender,
            "content": response,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        self.outbox.append(outbox_entry)
        return response

    def process(self, message: Any, sender: str = "manager") -> Any:
        """Process incoming message and return response."""
        raise NotImplementedError("Agents must implement the process method.")

    def clear_mailboxes(self) -> None:
        """Clear agent inbox and outbox."""
        self.inbox.clear()
        self.outbox.clear()


__all__ = ["BaseAgent"]

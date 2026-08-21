"""Dummy echo agent for Hive communication testing."""

from typing import Any
from mitchell.hive.agents.base import BaseAgent


class EchoAgent(BaseAgent):
    """Simple agent that echoes received messages."""

    def __init__(self, agent_id: str = "echo_agent", description: str = "Echoes messages back") -> None:
        super().__init__(agent_id=agent_id, description=description)

    def process(self, message: Any, sender: str = "manager") -> str:
        """Echo the incoming message."""
        return f"[EchoAgent] Received from {sender}: {message}"


__all__ = ["EchoAgent"]

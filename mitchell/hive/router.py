"""Hive router for registering agents and dispatching messages across all pillars."""

from typing import Any, Dict, List, Optional
from mitchell.core.logging import logger
from mitchell.hive.agents.android_worker import AndroidWorkerAgent
from mitchell.hive.agents.base import BaseAgent
from mitchell.hive.agents.browser_worker import BrowserWorkerAgent
from mitchell.hive.agents.echo import EchoAgent
from mitchell.hive.agents.efficiency_worker import EfficiencyWorkerAgent
from mitchell.hive.agents.windows_worker import WindowsWorkerAgent


class HiveRouter:
    """Routes messages, manages agent inboxes/outboxes, and coordinates Hive agents."""

    def __init__(self) -> None:
        self._agents: Dict[str, BaseAgent] = {}
        # Register default Hive agents across all pillars
        self.register_agent(EchoAgent())
        self.register_agent(BrowserWorkerAgent())
        self.register_agent(WindowsWorkerAgent())
        self.register_agent(AndroidWorkerAgent())
        self.register_agent(EfficiencyWorkerAgent())

    def register_agent(self, agent: BaseAgent) -> None:
        """Register an agent in the Hive registry."""
        if not isinstance(agent, BaseAgent):
            raise TypeError(f"Expected BaseAgent instance, got {type(agent).__name__}")
        self._agents[agent.agent_id] = agent
        logger.debug("Hive: Registered agent '{}'", agent.agent_id)

    def get_agent(self, agent_id: str) -> Optional[BaseAgent]:
        """Retrieve an agent by ID."""
        return self._agents.get(agent_id)

    def list_agents(self) -> List[Dict[str, str]]:
        """Return metadata for all registered Hive agents."""
        return [
            {"agent_id": agent.agent_id, "description": agent.description}
            for agent in self._agents.values()
        ]

    def send_message(self, agent_id: str, message: Any, sender: str = "manager") -> Any:
        """Send a message to an agent's inbox, process it, and return the result."""
        agent = self.get_agent(agent_id)
        if not agent:
            error_msg = f"Agent '{agent_id}' not found in Hive."
            logger.warning("Hive: {}", error_msg)
            return f"Error: {error_msg}"

        logger.debug("Hive: Sending message from '{}' to '{}'", sender, agent_id)
        result = agent.receive_message(message, sender=sender)
        logger.debug("Hive: Received response from '{}'", agent_id)
        return result

    def read_inbox(self, agent_id: str) -> List[Dict[str, Any]]:
        """Read message inbox for a specific agent."""
        agent = self.get_agent(agent_id)
        return list(agent.inbox) if agent else []

    def read_outbox(self, agent_id: str) -> List[Dict[str, Any]]:
        """Read message outbox for a specific agent."""
        agent = self.get_agent(agent_id)
        return list(agent.outbox) if agent else []


hive_router = HiveRouter()

__all__ = ["HiveRouter", "hive_router"]

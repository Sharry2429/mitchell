"""Hive router for registering agents and dispatching messages across all pillars and subsystems."""

from typing import Any, Dict, List, Optional
from mitchell.core.logging import logger
from mitchell.hive.agents.android_worker import AndroidWorkerAgent
from mitchell.hive.agents.base import BaseAgent
from mitchell.hive.agents.browser_worker import BrowserWorkerAgent
from mitchell.hive.agents.commerce_worker import CommerceWorkerAgent
from mitchell.hive.agents.comms_worker import CommsWorkerAgent
from mitchell.hive.agents.echo import EchoAgent
from mitchell.hive.agents.efficiency_worker import EfficiencyWorkerAgent
from mitchell.hive.agents.ide_worker import IDEWorkerAgent
from mitchell.hive.agents.iot_worker import IoTWorkerAgent
from mitchell.hive.agents.media_worker import MediaWorkerAgent
from mitchell.hive.agents.vision_worker import VisionWorkerAgent
from mitchell.hive.agents.windows_worker import WindowsWorkerAgent
from mitchell.hive.agents.workspace_worker import WorkspaceWorkerAgent


class HiveRouter:
    """Routes messages, manages agent inboxes/outboxes, coordinates static & dynamic Hive agents."""

    def __init__(self) -> None:
        self._agents: Dict[str, BaseAgent] = {}
        # Register default Hive agents across all pillars and subsystems
        self.register_agent(EchoAgent())
        self.register_agent(BrowserWorkerAgent())
        self.register_agent(WindowsWorkerAgent())
        self.register_agent(AndroidWorkerAgent())
        self.register_agent(EfficiencyWorkerAgent())
        self.register_agent(VisionWorkerAgent())
        self.register_agent(WorkspaceWorkerAgent())
        self.register_agent(IDEWorkerAgent())
        self.register_agent(CommsWorkerAgent())
        self.register_agent(MediaWorkerAgent())
        self.register_agent(CommerceWorkerAgent())
        self.register_agent(IoTWorkerAgent())

    def register_agent(self, agent: BaseAgent) -> None:
        """Register an agent in the Hive registry."""
        if not isinstance(agent, BaseAgent):
            raise TypeError(f"Expected BaseAgent instance, got {type(agent).__name__}")
        self._agents[agent.agent_id] = agent
        logger.debug("Hive: Registered agent '{}'", agent.agent_id)

    def unregister_agent(self, agent_id: str) -> bool:
        """Unregister an agent by ID."""
        if agent_id in self._agents:
            del self._agents[agent_id]
            return True
        return False

    def spawn_dynamic_agent(
        self,
        name: Optional[str] = None,
        description: str = "",
        system_prompt: str = "",
        allowed_tools: Optional[List[str]] = None,
        model_name: str = "fast",
        parent_agent_id: Optional[str] = None,
    ) -> Any:
        """Spawn a dynamic Hermes agent and register it in the router."""
        from mitchell.hive.dynamic import dynamic_swarm
        return dynamic_swarm.spawn(
            name=name,
            description=description,
            system_prompt=system_prompt,
            allowed_tools=allowed_tools,
            model_name=model_name,
            parent_agent_id=parent_agent_id,
        )

    def destroy_dynamic_agent(self, agent_id: str) -> bool:
        """Destroy and unregister a dynamic agent."""
        from mitchell.hive.dynamic import dynamic_swarm
        return dynamic_swarm.destroy(agent_id)

    def get_agent(self, agent_id: str) -> Optional[BaseAgent]:
        """Retrieve an agent by ID."""
        return self._agents.get(agent_id)

    def list_agents(self) -> List[Dict[str, Any]]:
        """Return metadata for all registered Hive agents (both static and dynamic)."""
        agents_list = []
        for agent in self._agents.values():
            is_dynamic = hasattr(agent, "scratchpad") or agent.__class__.__name__ == "HermesDynamicAgent"
            agents_list.append({
                "agent_id": agent.agent_id,
                "description": agent.description,
                "is_dynamic": is_dynamic,
                "status": getattr(agent, "status", "ready"),
                "model_name": getattr(agent, "model_name", "native"),
                "inbox_count": len(agent.inbox),
                "outbox_count": len(agent.outbox),
            })
        return agents_list

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

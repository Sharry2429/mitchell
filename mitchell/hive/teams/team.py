"""Pre-configured Agent Team formations for multi-agent workflows."""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from mitchell.core.event_log import event_log
from mitchell.core.logging import logger
from mitchell.hive.blackboard import blackboard
from mitchell.hive.router import HiveRouter, hive_router


class AgentTeam(BaseModel):
    """Team definition grouping agents for domain workflows."""

    team_name: str
    description: str
    agent_ids: List[str]
    default_leader: str = "manager"


class TeamCoordinator:
    """Coordinates specialized agent team formations across the Blackboard."""

    def __init__(self, router: Optional[HiveRouter] = None) -> None:
        self.hive = router or hive_router
        self.board = blackboard
        self._teams: Dict[str, AgentTeam] = {}
        self._seed_default_teams()

    def _seed_default_teams(self) -> None:
        """Register default multi-agent teams."""
        self.register_team(AgentTeam(
            team_name="research_team",
            description="Autonomous web research, extraction, and synthesis team",
            agent_ids=["browser_worker", "vision_worker"],
        ))
        self.register_team(AgentTeam(
            team_name="cross_device_team",
            description="Multi-device desktop and mobile automation team",
            agent_ids=["windows_worker", "android_worker", "vision_worker"],
        ))
        self.register_team(AgentTeam(
            team_name="optimization_team",
            description="System optimization, token compression, and prompt audit team",
            agent_ids=["efficiency_worker"],
        ))
        self.register_team(AgentTeam(
            team_name="finance_team",
            description="Autonomous financial intelligence, stock/crypto analysis, technical indicators, and risk critique",
            agent_ids=["browser_worker", "vision_worker"],
        ))

    def register_team(self, team: AgentTeam) -> None:
        """Register a team formation."""
        self._teams[team.team_name] = team
        logger.debug("Registered agent team '{}' with {} agents", team.team_name, len(team.agent_ids))

    def get_team(self, team_name: str) -> Optional[AgentTeam]:
        """Retrieve team definition."""
        return self._teams.get(team_name)

    def list_teams(self) -> List[Dict[str, Any]]:
        """List all available agent teams."""
        return [
            {
                "team_name": t.team_name,
                "description": t.description,
                "agents": t.agent_ids,
            }
            for t in self._teams.values()
        ]

    def dispatch_team(self, team_name: str, task: str) -> Dict[str, Any]:
        """Dispatch a collective task to an agent team, posting artifacts to Blackboard."""
        team = self.get_team(team_name)
        if not team:
            return {"status": "error", "error": f"Team '{team_name}' not found"}

        logger.info("TeamCoordinator: Dispatching task '{}' to team '{}'", task, team_name)
        self.board.post(
            topic=f"team:{team_name}",
            content={"task": task, "agents": team.agent_ids},
            author="team_coordinator",
        )

        results: Dict[str, Any] = {}
        for agent_id in team.agent_ids:
            try:
                res = self.hive.send_message(agent_id=agent_id, message=task, sender=f"team:{team_name}")
                results[agent_id] = res
                self.board.post(
                    topic=f"team:{team_name}",
                    content={"agent_id": agent_id, "result": str(res)[:200]},
                    author=agent_id,
                )
            except Exception as e:
                results[agent_id] = f"Error: {e}"

        event_log.log_event(
            "team_task_executed",
            source="team_coordinator",
            data={"team": team_name, "agents_count": len(team.agent_ids)},
        )

        return {
            "status": "success",
            "team_name": team_name,
            "results": results,
        }


team_coordinator = TeamCoordinator()

__all__ = ["AgentTeam", "TeamCoordinator", "team_coordinator"]

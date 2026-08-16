"""
mitchell.agents.team
====================
The Teammate Tool exposed to Mitchell's own orchestrator.
"""

import uuid
from mitchell.agents.hive import get_hive

_hive = get_hive()

# In-memory roster of active team members for this session.
_active_team = {}

from mitchell.core.warm_pool import claim_worker

def team_spawn(role: str, task: str, priority: str = "normal") -> str:
    """
    Spawn a teammate for a specific role and task.
    In v1, this will claim a warm pool worker (simulated here) and dispatch.
    Returns the agent_id.
    """
    worker = claim_worker(role)
    if not worker:
        raise ValueError(f"Unknown or unsupported role: {role}")
        
    agent_id = f"{role}-{uuid.uuid4().hex[:8]}"
    _active_team[agent_id] = {
        "role": role,
        "task": task,
        "status": "starting",
        "worker_state": worker
    }
    
    # Send the initial task message
    _hive.send_message("orchestrator", agent_id, f"TASK: {task}\nPRIORITY: {priority}")
    _hive.write_event("orchestrator", "spawn", {"agent_id": agent_id, "role": role})
    
    return agent_id

def team_message(agent_id: str, content: str) -> None:
    """Send a message to an active teammate."""
    if agent_id not in _active_team:
        raise ValueError(f"Unknown teammate: {agent_id}")
    _hive.send_message("orchestrator", agent_id, content)

def team_status(agent_id: str | None = None) -> dict:
    """Get status of a specific teammate, or the whole roster."""
    # Reads from event log in real system to determine status
    if agent_id:
        return _active_team.get(agent_id, {"error": "Not found"})
    return _active_team

def team_dismiss(agent_id: str) -> None:
    """Dismiss a teammate."""
    if agent_id in _active_team:
        _hive.send_message("orchestrator", agent_id, "SYSTEM: SHUTDOWN")
        _hive.write_event("orchestrator", "dismiss", {"agent_id": agent_id})
        del _active_team[agent_id]


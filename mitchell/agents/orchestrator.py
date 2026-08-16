"""
mitchell.agents.orchestrator
Decides the execution shape per task and orchestrates execution.
"""
import logging
from typing import Any, Dict

from mitchell.core.fast_intent import resolve_intent
from mitchell.core.tool_registry import get_registered_tools
from mitchell.agents.team import team_spawn

logger = logging.getLogger("mitchell.agents.orchestrator")

class Orchestrator:
    def __init__(self):
        self.tools = get_registered_tools()
        
    def execute(self, task: str) -> str:
        # 1. Fast Path (Tier 0 / Tier 1)
        fast_res = resolve_intent(task)
        if fast_res:
            tool_name, args = fast_res
            logger.info(f"Fast path match: {tool_name}")
            return self._execute_tool(tool_name, args)
            
        # 2. Heuristics for Team vs Single loop vs Parallel
        lower_task = task.lower()
        if "research" in lower_task or "code" in lower_task or "team" in lower_task:
            return self._dispatch_to_team(task)
            
        # Fallback to single agent loop for complex single-pillar tasks
        return self._single_agent_loop(task)
        
    def _execute_tool(self, tool_name: str, args: dict) -> str:
        if tool_name in self.tools:
            try:
                res = self.tools[tool_name](**args)
                return f"Success: {res}"
            except Exception as e:
                return f"Error executing {tool_name}: {e}"
        return f"Tool {tool_name} not found"

    def _single_agent_loop(self, task: str) -> str:
        # Placeholder for full single agent loop (ReAct)
        logger.info("Executing via single agent loop")
        return "Single agent loop executed."
        
    def _dispatch_to_team(self, task: str) -> str:
        logger.info("Dispatching to team")
        role = "windows_worker"
        if "android" in task.lower():
            role = "android_worker"
        elif "browser" in task.lower():
            role = "browser_worker"
        elif "code" in task.lower():
            role = "coder"
        elif "research" in task.lower():
            role = "researcher"
            
        try:
            agent_id = team_spawn(role, task)
            return f"Dispatched to team: {role} (ID: {agent_id})"
        except Exception as e:
            return f"Error dispatching to team: {e}"

"""Structured Task Graph Planner synthesizing executable subtask dependencies."""

import uuid
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from mitchell.core.event_log import event_log
from mitchell.core.llm import model_router
from mitchell.core.logging import logger
from mitchell.manager.classifier import GoalClassification


class TaskNode(BaseModel):
    """Individual node in the execution Task Graph."""

    id: str = Field(default_factory=lambda: f"task_{uuid.uuid4().hex[:6]}")
    title: str = Field(..., description="Short title of the subtask")
    target_agent: str = Field(..., description="Target Hive agent ID (e.g. browser_worker, windows_worker, android_worker)")
    action: str = Field(..., description="Specific worker action command")
    payload: Dict[str, Any] = Field(default_factory=dict, description="Action arguments")
    dependencies: List[str] = Field(default_factory=list, description="IDs of prerequisite tasks")
    status: str = Field(default="pending", description="pending | in_progress | completed | failed")


class TaskGraph(BaseModel):
    """Directed acyclic task plan containing executable subtasks."""

    id: str = Field(default_factory=lambda: f"plan_{uuid.uuid4().hex[:8]}")
    goal: str = Field(..., description="Original user goal")
    nodes: List[TaskNode] = Field(default_factory=list, description="Sequential or dependent subtask nodes")
    created_at: str = Field(default_factory=lambda: uuid.uuid4().hex)


class TaskPlanner:
    """Decomposes goals into structured Task Graphs following Karpathy principles."""

    def __init__(self) -> None:
        self.router = model_router

    async def create_plan(
        self,
        goal: str,
        classification: GoalClassification,
        memory_context: Optional[List[Dict[str, Any]]] = None,
    ) -> TaskGraph:
        """Synthesize structured TaskGraph for user goal."""
        logger.info("TaskPlanner: Formulating plan for goal '{}' ({})", goal, classification.domain)

        nodes: List[TaskNode] = []

        if classification.domain == "browser":
            # Direct or multi-step browser plan
            nodes.append(TaskNode(
                title="Navigate to target URL",
                target_agent="browser_worker",
                action="goto",
                payload={"url": self._extract_url_or_default(goal)},
            ))
            nodes.append(TaskNode(
                title="Capture page snapshot",
                target_agent="browser_worker",
                action="snapshot",
                payload={},
                dependencies=[nodes[0].id],
            ))

        elif classification.domain == "windows":
            nodes.append(TaskNode(
                title="Launch application",
                target_agent="windows_worker",
                action="launch",
                payload={"cmd": self._extract_app_or_default(goal)},
            ))

        elif classification.domain == "android":
            nodes.append(TaskNode(
                title="Mobile task execution",
                target_agent="android_worker",
                action="key",
                payload={"key": "HOME"},
            ))

        elif classification.domain == "multi_pillar":
            # Example cross-pillar sequence
            t1 = TaskNode(
                title="Fetch web information",
                target_agent="browser_worker",
                action="goto",
                payload={"url": self._extract_url_or_default(goal)},
            )
            t2 = TaskNode(
                title="Record data in Windows Notepad",
                target_agent="windows_worker",
                action="launch",
                payload={"cmd": "notepad.exe"},
                dependencies=[t1.id],
            )
            nodes.extend([t1, t2])

        else:
            nodes.append(TaskNode(
                title="Direct Manager execution",
                target_agent="echo_agent",
                action="process",
                payload={"message": goal},
            ))

        graph = TaskGraph(goal=goal, nodes=nodes)

        event_log.log_event(
            "task_plan_synthesized",
            source="task_planner",
            data={"plan_id": graph.id, "nodes_count": len(graph.nodes), "domain": classification.domain},
        )

        return graph

    def _extract_url_or_default(self, text: str) -> str:
        words = text.split()
        for w in words:
            if w.startswith("http://") or w.startswith("https://") or ("." in w and "/" in w):
                return w
        return "https://news.ycombinator.com"

    def _extract_app_or_default(self, text: str) -> str:
        lower = text.lower()
        if "notepad" in lower:
            return "notepad.exe"
        if "calc" in lower:
            return "calc.exe"
        if "explorer" in lower:
            return "explorer.exe"
        return "notepad.exe"


task_planner = TaskPlanner()

__all__ = ["TaskNode", "TaskGraph", "TaskPlanner", "task_planner"]

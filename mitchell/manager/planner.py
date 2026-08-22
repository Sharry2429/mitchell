"""Structured Task Graph Planner synthesizing executable subtask dependencies across all Hive workers."""

import uuid
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from mitchell.core.event_log import event_log
from mitchell.core.llm import model_router
from mitchell.core.logging import logger
from mitchell.core.prompts import MITCHELL_PLANNER_SYSTEM_PROMPT
from mitchell.manager.classifier import GoalClassification


class TaskNode(BaseModel):
    """Individual node in the execution Task Graph."""

    id: str = Field(default_factory=lambda: f"task_{uuid.uuid4().hex[:6]}")
    title: str = Field(..., description="Short title of the subtask")
    target_agent: str = Field(..., description="Target Hive agent ID (e.g. browser_worker, windows_worker, workspace_worker, ide_worker, comms_worker, media_worker, commerce_worker, iot_worker)")
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

        if classification.domain == "workspace":
            nodes.append(TaskNode(
                title="Execute workspace operation",
                target_agent="workspace_worker",
                action="summary" if "summary" in goal.lower() else "document",
                payload={"title": goal[:40], "raw": goal},
            ))

        elif classification.domain == "ide":
            nodes.append(TaskNode(
                title="Execute IDE engineering task",
                target_agent="ide_worker",
                action="test" if "test" in goal.lower() or "pytest" in goal.lower() else ("command" if "run" in goal.lower() else "write_file"),
                payload={"raw": goal, "command": goal},
            ))

        elif classification.domain == "comms":
            nodes.append(TaskNode(
                title="Execute communication dispatch",
                target_agent="comms_worker",
                action="whatsapp" if "whatsapp" in goal.lower() else ("sms" if "sms" in goal.lower() else "inbox"),
                payload={"raw": goal, "message": goal},
            ))

        elif classification.domain == "media":
            nodes.append(TaskNode(
                title="Execute media playback / download",
                target_agent="media_worker",
                action="spotify" if "spotify" in goal.lower() or "music" in goal.lower() or "play" in goal.lower() else "download",
                payload={"raw": goal, "query": goal, "url": self._extract_url_or_default(goal)},
            ))

        elif classification.domain == "commerce":
            nodes.append(TaskNode(
                title="Execute commerce search / tracking",
                target_agent="commerce_worker",
                action="track" if "track" in goal.lower() else ("coupons" if "coupon" in goal.lower() or "deal" in goal.lower() else "search"),
                payload={"raw": goal, "query": goal},
            ))

        elif classification.domain == "iot":
            nodes.append(TaskNode(
                title="Execute smart home action",
                target_agent="iot_worker",
                action="scene" if "scene" in goal.lower() or "cinema" in goal.lower() or "focus" in goal.lower() else "light_on",
                payload={"raw": goal, "scene": "cinema_mode" if "cinema" in goal.lower() else "focus_work"},
            ))

        elif classification.domain == "browser":
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
            t1 = TaskNode(
                title="Fetch web information",
                target_agent="browser_worker",
                action="goto",
                payload={"url": self._extract_url_or_default(goal)},
            )
            t2 = TaskNode(
                title="Record findings in Native Workspace",
                target_agent="workspace_worker",
                action="create_doc",
                payload={"title": f"Report — {goal[:30]}", "content": goal},
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

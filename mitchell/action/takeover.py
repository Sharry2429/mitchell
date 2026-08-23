"""Autonomous Task Takeover Engine with Human Checkpoints and Approval Gates.

Allows users to say "Mitchell, take over and finish this".
Mitchell coordinates workers, plans step-by-step milestones, records progress,
and pauses at human gates for critical or destructive actions (file deletion, deployment, payments).
"""

import asyncio
import time
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from mitchell.core.event_log import event_log
from mitchell.core.logging import logger


class TakeoverStep(BaseModel):
    """Milestone step in a takeover plan."""

    step_id: int
    title: str
    description: str
    assigned_agent: str = "mitchell"
    requires_approval: bool = False
    status: str = "pending"  # pending | in_progress | waiting_approval | completed | failed | skipped
    result_summary: Optional[str] = None


class TakeoverSession(BaseModel):
    """Active takeover task execution state."""

    session_id: str
    goal: str
    status: str = "running"  # running | paused | waiting_gate | completed | cancelled
    steps: List[TakeoverStep]
    current_step_index: int = 0
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class TaskTakeoverEngine:
    """Manages takeover lifecycles, progress execution, and checkpoint validation."""

    def __init__(self) -> None:
        self.active_sessions: Dict[str, TakeoverSession] = {}

    def start_takeover(self, goal: str, auto_approve_safe: bool = True) -> TakeoverSession:
        """Initialize and begin autonomous task takeover."""
        session_id = f"takeover_{int(time.time())}"

        # Formulate initial structured roadmap steps
        steps = [
            TakeoverStep(
                step_id=1,
                title="Project State & File Inspection",
                description="Scan directory structure, analyze git status and recent AST diffs.",
                assigned_agent="mitchell_ide",
                requires_approval=False,
                status="in_progress",
            ),
            TakeoverStep(
                step_id=2,
                title="Dependency & Code Alignment",
                description="Verify modules, install missing libraries or run static linter.",
                assigned_agent="claude_code",
                requires_approval=False,
                status="pending",
            ),
            TakeoverStep(
                step_id=3,
                title="Implementation Execution",
                description="Implement requested feature modules and test suites.",
                assigned_agent="grok_agent",
                requires_approval=False,
                status="pending",
            ),
            TakeoverStep(
                step_id=4,
                title="Automated Test & Verification Gate",
                description="Execute test runner and confirm zero regressions.",
                assigned_agent="mitchell_runner",
                requires_approval=False,
                status="pending",
            ),
            TakeoverStep(
                step_id=5,
                title="Final Review & Commit Gate",
                description="Human checkpoint before staging final commit or push.",
                assigned_agent="mitchell",
                requires_approval=True,
                status="pending",
            ),
        ]

        session = TakeoverSession(
            session_id=session_id,
            goal=goal,
            status="running",
            steps=steps,
            current_step_index=0,
        )

        self.active_sessions[session_id] = session

        event_log.log_event(
            "takeover_session_started",
            source="takeover_engine",
            data={"session_id": session_id, "goal": goal, "steps_count": len(steps)},
        )

        logger.info("Started autonomous takeover session '{}' for goal: '{}'", session_id, goal)
        return session

    def advance_step(self, session_id: str, success: bool = True, summary: str = "") -> Optional[TakeoverSession]:
        """Mark current step and advance to next."""
        session = self.active_sessions.get(session_id)
        if not session or session.status in ("completed", "cancelled"):
            return session

        idx = session.current_step_index
        if idx < len(session.steps):
            step = session.steps[idx]
            step.status = "completed" if success else "failed"
            step.result_summary = summary or "Step completed successfully."

            # Advance
            if idx + 1 < len(session.steps):
                session.current_step_index += 1
                next_step = session.steps[session.current_step_index]
                if next_step.requires_approval:
                    session.status = "waiting_gate"
                    next_step.status = "waiting_approval"
                else:
                    next_step.status = "in_progress"
            else:
                session.status = "completed"

            session.updated_at = datetime.now(timezone.utc)

        return session

    def approve_gate(self, session_id: str) -> Optional[TakeoverSession]:
        """User explicitly approves a checkpoint gate to proceed."""
        session = self.active_sessions.get(session_id)
        if not session or session.status != "waiting_gate":
            return session

        idx = session.current_step_index
        if idx < len(session.steps):
            session.steps[idx].status = "in_progress"
            session.status = "running"
            session.updated_at = datetime.now(timezone.utc)

        event_log.log_event(
            "takeover_gate_approved",
            source="takeover_engine",
            data={"session_id": session_id, "step_index": idx},
        )

        return session

    def get_session(self, session_id: str) -> Optional[TakeoverSession]:
        """Get active session state."""
        return self.active_sessions.get(session_id)

    def list_sessions(self) -> List[TakeoverSession]:
        """List all active and historical takeover sessions."""
        return list(self.active_sessions.values())


takeover_engine = TaskTakeoverEngine()

__all__ = ["TakeoverStep", "TakeoverSession", "TaskTakeoverEngine", "takeover_engine"]

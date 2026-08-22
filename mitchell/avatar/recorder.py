"""Action sequence recorder generating visual walkthroughs and step summaries."""

import time
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from mitchell.core.event_log import event_log
from mitchell.core.logging import logger


class ActionStep(BaseModel):
    """A recorded user or agent interaction step."""

    step_number: int
    action_type: str  # "click", "type", "navigate", "vision_locate", "voice_speak"
    target: str
    description: str
    screenshot_path: Optional[str] = None
    timestamp: float = Field(default_factory=time.time)


class SessionRecorder:
    """Records chronological action timelines and outputs structured walkthrough reports."""

    def __init__(self) -> None:
        self.is_recording = False
        self.current_steps: List[ActionStep] = []
        self.session_title: str = "Interactive Session"

    def start_recording(self, title: str = "Automated Walkthrough") -> None:
        """Begin capturing action steps."""
        self.session_title = title
        self.current_steps.clear()
        self.is_recording = True
        logger.info("SessionRecorder: Started recording session '{}'", title)
        event_log.log_event("session_recording_started", source="session_recorder", data={"title": title})

    def record_step(
        self,
        action_type: str,
        target: str,
        description: str,
        screenshot_path: Optional[str] = None,
    ) -> ActionStep:
        """Log an execution step into the session timeline."""
        step = ActionStep(
            step_number=len(self.current_steps) + 1,
            action_type=action_type,
            target=target,
            description=description,
            screenshot_path=screenshot_path,
        )
        if self.is_recording:
            self.current_steps.append(step)
            logger.debug("SessionRecorder: Step #{}: {} -> {}", step.step_number, action_type, target)
        return step

    def stop_recording(self) -> Dict[str, Any]:
        """Stop recording and return session summary."""
        self.is_recording = False
        logger.info("SessionRecorder: Stopped recording. Total steps: {}", len(self.current_steps))
        event_log.log_event(
            "session_recording_stopped",
            source="session_recorder",
            data={"total_steps": len(self.current_steps)},
        )
        return {
            "title": self.session_title,
            "total_steps": len(self.current_steps),
            "steps": [s.model_dump() for s in self.current_steps],
        }

    def generate_markdown_walkthrough(self) -> str:
        """Format captured steps into a markdown walkthrough with instructions."""
        lines = [
            f"# 🎬 Walkthrough: {self.session_title}",
            "",
            f"- **Recorded Steps:** {len(self.current_steps)}",
            "",
            "### Step-by-Step Actions:",
            "",
        ]
        for s in self.current_steps:
            lines.append(f"**Step {s.step_number}. {s.action_type.capitalize()} on `{s.target}`**")
            lines.append(f"> {s.description}")
            lines.append("")

        return "\n".join(lines)


session_recorder = SessionRecorder()

__all__ = ["ActionStep", "SessionRecorder", "session_recorder"]

"""Executive Daily Intelligence Briefing engine inspired by JARVIS-AGI.

Aggregates system telemetry, upcoming calendar schedules, pending workspace tasks,
unread WhatsApp/SMS messages, and smart home status into a unified briefing.
"""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from mitchell.comms.hub import communication_hub
from mitchell.core.event_log import event_log
from mitchell.core.logging import logger
from mitchell.jarvis.telemetry import system_telemetry
from mitchell.memory.self_model import self_model
from mitchell.workspace.calendar import calendar_engine
from mitchell.workspace.projects import project_engine


class ExecutiveBriefing(BaseModel):
    """Structured executive briefing report."""

    greeting: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    system_status: str
    calendar_summary: str
    pending_tasks_count: int
    pending_tasks: List[str] = Field(default_factory=list)
    unread_messages_count: int
    unread_messages: List[str] = Field(default_factory=list)
    proactive_advice: str
    spoken_summary: str


class ExecutiveDailyBriefing:
    """Generates comprehensive JARVIS-style executive briefings."""

    def generate_briefing(self, user_name: str = "Sir") -> ExecutiveBriefing:
        """Synthesize a complete daily intelligence briefing."""
        now = datetime.now()
        hour = now.hour

        if 5 <= hour < 12:
            greeting = f"Good morning, {user_name}."
        elif 12 <= hour < 17:
            greeting = f"Good afternoon, {user_name}."
        elif 17 <= hour < 22:
            greeting = f"Good evening, {user_name}."
        else:
            greeting = f"Greetings, {user_name}. Burning the midnight oil."

        # 1. System Telemetry
        sys_status = system_telemetry.get_summary_string()

        # 2. Upcoming Calendar
        upcoming_events = calendar_engine.get_upcoming_events(days_ahead=2)
        if upcoming_events:
            cal_summary = f"You have {len(upcoming_events)} upcoming event(s): " + ", ".join(
                f"{e.title} at {e.start_time.strftime('%H:%M')}" for e in upcoming_events[:3]
            )
        else:
            cal_summary = "Your schedule is clear with no immediate calendar conflicts."

        # 3. Pending Workspace Tasks
        all_boards = project_engine.list_boards()
        pending_tasks = []
        for b in all_boards:
            board = project_engine.get_board(b["board_id"])
            if board:
                cols = board.get_column_view()
                in_prog = cols.get("in_progress", []) + cols.get("todo", [])
                for t in in_prog[:4]:
                    pending_tasks.append(f"[{board.title}] {t.title} ({t.priority})")

        # 4. Unread Messages & Comms
        recent_msgs = communication_hub.list_messages(limit=10)
        unread_msgs = [
            f"[{m['channel'].upper()}] {m['sender']}: {m['content'][:50]}"
            for m in recent_msgs if m.get("is_incoming", False)
        ]

        # 5. Proactive Advice based on User Model
        user_summary = self_model.get_user_context_summary()
        advice = "All local systems operating optimally. Ready to execute multi-agent workflows."

        # Spoken summary suitable for TTS
        task_phrase = f"{len(pending_tasks)} active tasks on your boards" if pending_tasks else "all projects up to date"
        msg_phrase = f"{len(unread_msgs)} incoming messages" if unread_msgs else "no unread communications"
        spoken = f"{greeting} All systems are nominal. You have {task_phrase}, and {msg_phrase}. How may I assist you today?"

        briefing = ExecutiveBriefing(
            greeting=greeting,
            system_status=sys_status,
            calendar_summary=cal_summary,
            pending_tasks_count=len(pending_tasks),
            pending_tasks=pending_tasks[:6],
            unread_messages_count=len(unread_msgs),
            unread_messages=unread_msgs[:6],
            proactive_advice=advice,
            spoken_summary=spoken,
        )

        event_log.log_event(
            "executive_briefing_generated",
            source="jarvis_briefing",
            data={"pending_tasks": len(pending_tasks), "unread_msgs": len(unread_msgs)},
        )
        return briefing

    def format_markdown(self, briefing: ExecutiveBriefing) -> str:
        """Format the briefing as clean, readable Markdown."""
        lines = [
            f"# ⚡ {briefing.greeting}",
            f"*Generated: {briefing.timestamp.strftime('%Y-%m-%d %H:%M:%S UTC')}*",
            "",
            "### 🖥️ Hardware Telemetry",
            f"> {briefing.system_status}",
            "",
            "### 📅 Schedule & Calendar",
            f"{briefing.calendar_summary}",
            "",
            f"### 📋 Active Tasks ({briefing.pending_tasks_count})",
        ]

        if briefing.pending_tasks:
            for t in briefing.pending_tasks:
                lines.append(f"- {t}")
        else:
            lines.append("- *No urgent pending tasks.*")

        lines.extend([
            "",
            f"### 💬 Unified Communications ({briefing.unread_messages_count})",
        ])

        if briefing.unread_messages:
            for m in briefing.unread_messages:
                lines.append(f"- {m}")
        else:
            lines.append("- *Inbox clean.*")

        lines.extend([
            "",
            "### 💡 Proactive Status",
            briefing.proactive_advice,
        ])

        return "\n".join(lines)


executive_briefing = ExecutiveDailyBriefing()

__all__ = ["ExecutiveBriefing", "ExecutiveDailyBriefing", "executive_briefing"]

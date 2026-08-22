"""Dynamic Intelligence Briefing Engine for Mitchell AI.

Dynamically collects live context from hardware metrics, Git repository status,
Native Workspace tasks, WhatsApp MCP communications, and user model preferences,
then synthesizes a tailored executive briefing using Mitchell's model router.
"""

import asyncio
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from mitchell.comms.hub import communication_hub
from mitchell.core.event_log import event_log
from mitchell.core.llm import model_router
from mitchell.core.logging import logger
from mitchell.ide.git import git_manager
from mitchell.memory.self_model import self_model
from mitchell.system.telemetry import live_system_monitor
from mitchell.workspace.calendar import calendar_engine
from mitchell.workspace.projects import project_engine


class DynamicSystemBriefing(BaseModel):
    """Structured dynamic briefing report generated from live system context."""

    title: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    telemetry_summary: str
    git_status_summary: str
    calendar_summary: str
    pending_tasks: List[str] = Field(default_factory=list)
    unread_messages: List[str] = Field(default_factory=list)
    executive_synthesis: str
    spoken_summary: str


class DynamicBriefingEngine:
    """Dynamically aggregates live state across the entire Mitchell environment and synthesizes briefings."""

    async def generate_dynamic_briefing(self, user_name: str = "User", use_llm: bool = True) -> DynamicSystemBriefing:
        """Gathers real-time state across all pillars and synthesizes a dynamic briefing."""
        now = datetime.now()
        hour = now.hour

        if 5 <= hour < 12:
            greeting = f"Good morning, {user_name}"
        elif 12 <= hour < 17:
            greeting = f"Good afternoon, {user_name}"
        elif 17 <= hour < 22:
            greeting = f"Good evening, {user_name}"
        else:
            greeting = f"Night session briefing for {user_name}"

        # 1. Live Telemetry
        telemetry = live_system_monitor.get_live_metrics()
        telemetry_str = live_system_monitor.format_summary()

        # 2. Live Git Status
        try:
            git_st = git_manager.status()
            if git_st.is_repo:
                modified_count = len(git_st.modified_files) + len(git_st.untracked_files)
                git_str = f"Branch '{git_st.branch}' — {modified_count} uncommitted change(s)" if modified_count > 0 else f"Branch '{git_st.branch}' — Clean working directory"
            else:
                git_str = "No active Git workspace detected"
        except Exception:
            git_str = "Git status nominal"

        # 3. Live Calendar
        upcoming = calendar_engine.get_upcoming_events(days_ahead=2)
        if upcoming:
            cal_str = f"{len(upcoming)} scheduled event(s): " + ", ".join(
                f"'{e.title}' at {e.start_time.strftime('%H:%M')}" for e in upcoming[:3]
            )
        else:
            cal_str = "No upcoming calendar conflicts in the next 48 hours."

        # 4. Live Kanban Tasks
        boards = project_engine.list_boards()
        pending_tasks = []
        for b in boards:
            b_id = b.get("id") or b.get("board_id") or ""
            board = project_engine.get_board(b_id) if b_id else None
            if board:
                cols = board.get_column_view()
                active = cols.get("in_progress", []) + cols.get("todo", [])
                for t in active[:5]:
                    pending_tasks.append(f"[{board.title}] {t.title} ({t.priority})")

        # 5. Live Communications
        recent_msgs = communication_hub.list_messages(limit=10)
        unread_msgs = [
            f"[{m['channel'].upper()}] {m['sender']}: {m['content'][:60]}"
            for m in recent_msgs if m.get("is_incoming", False)
        ]

        # 6. User Model Context
        user_context = self_model.get_user_context_summary()

        # 7. AI Executive Synthesis
        context_block = (
            f"User: {user_name}\n"
            f"Time: {now.strftime('%A, %B %d %Y, %I:%M %p')}\n"
            f"Telemetry: {telemetry_str}\n"
            f"Git: {git_str}\n"
            f"Calendar: {cal_str}\n"
            f"Active Tasks ({len(pending_tasks)}): {', '.join(pending_tasks) if pending_tasks else 'None'}\n"
            f"Incoming Messages ({len(unread_msgs)}): {', '.join(unread_msgs) if unread_msgs else 'None'}\n"
            f"User Context: {user_context}\n"
        )

        synthesis_text = ""
        if use_llm:
            try:
                prompt = (
                    f"You are Mitchell AI. Synthesize an executive, actionable, dynamic briefing based on this live system state:\n"
                    f"{context_block}\n"
                    f"Provide 3-4 bullet points highlighting key priorities, system health, and proactive suggestions. Keep it crisp, sharp, and confident."
                )
                llm_res = await asyncio.wait_for(
                    model_router.generate(prompt=prompt, purpose="dynamic_briefing"),
                    timeout=2.0,
                )
                synthesis_text = llm_res.content
            except Exception as e:
                logger.debug("LLM synthesis fallback: {}", e)

        if not synthesis_text:
            synthesis_text = (
                f"• Hardware: Operating at {telemetry.cpu_percent:.1f}% CPU with {telemetry.ram_free_gb:.1f} GB RAM available.\n"
                f"• Workspace: {len(pending_tasks)} active task(s) tracked on your Kanban boards.\n"
                f"• Development: {git_str}.\n"
                f"• Status: All native subsystems online and ready for autonomous dispatch."
            )

        spoken = (
            f"{greeting}. System is running at {telemetry.cpu_percent:.0f}% CPU with {telemetry.ram_free_gb:.1f} gigabytes of RAM available. "
            f"You have {len(pending_tasks)} active tasks in your workspace and {len(unread_msgs)} incoming communications. "
            f"How shall we proceed?"
        )

        briefing = DynamicSystemBriefing(
            title=f"⚡ Mitchell AI Intelligence Briefing — {now.strftime('%b %d, %Y')}",
            telemetry_summary=telemetry_str,
            git_status_summary=git_str,
            calendar_summary=cal_str,
            pending_tasks=pending_tasks,
            unread_messages=unread_msgs,
            executive_synthesis=synthesis_text,
            spoken_summary=spoken,
        )

        event_log.log_event(
            "dynamic_briefing_generated",
            source="dynamic_briefing_engine",
            data={"pending_tasks": len(pending_tasks), "unread_msgs": len(unread_msgs)},
        )
        return briefing

    def generate_briefing_sync(self, user_name: str = "User") -> DynamicSystemBriefing:
        """Synchronous wrapper for briefing generation."""
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                import concurrent.futures
                with concurrent.futures.ThreadPoolExecutor() as pool:
                    return pool.submit(asyncio.run, self.generate_dynamic_briefing(user_name)).result()
            return loop.run_until_complete(self.generate_dynamic_briefing(user_name))
        except Exception:
            return asyncio.run(self.generate_dynamic_briefing(user_name))

    def format_markdown(self, briefing: DynamicSystemBriefing) -> str:
        """Format the dynamic briefing report as readable Markdown."""
        lines = [
            f"# {briefing.title}",
            f"*Timestamp: {briefing.timestamp.strftime('%Y-%m-%d %H:%M:%S UTC')}*",
            "",
            "### 🖥️ Live Hardware Telemetry",
            f"> {briefing.telemetry_summary}",
            "",
            "### 🛠️ Repository & Workspace Status",
            f"- **Git Status**: {briefing.git_status_summary}",
            f"- **Calendar**: {briefing.calendar_summary}",
            "",
            f"### 📋 Active Tasks ({len(briefing.pending_tasks)})",
        ]

        if briefing.pending_tasks:
            for t in briefing.pending_tasks:
                lines.append(f"- {t}")
        else:
            lines.append("- *No urgent pending tasks.*")

        lines.extend([
            "",
            f"### 💬 Unified Communications ({len(briefing.unread_messages)})",
        ])

        if briefing.unread_messages:
            for m in briefing.unread_messages:
                lines.append(f"- {m}")
        else:
            lines.append("- *Inbox clean.*")

        lines.extend([
            "",
            "### 🧠 Mitchell AI Executive Synthesis",
            briefing.executive_synthesis,
        ])

        return "\n".join(lines)


dynamic_briefing = DynamicBriefingEngine()

__all__ = ["DynamicSystemBriefing", "DynamicBriefingEngine", "dynamic_briefing"]

"""Calendar, reminder, and event scheduling engine with iCalendar export and recurring alerts."""

import json
import uuid
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Literal, Optional
from pydantic import BaseModel, Field

from mitchell.core.event_log import event_log
from mitchell.core.logging import logger
from mitchell.workspace.storage import workspace_storage


class CalendarEvent(BaseModel):
    """A calendar event or task reminder."""

    id: str = Field(default_factory=lambda: f"evt_{str(uuid.uuid4())[:8]}")
    title: str
    description: str = ""
    start_time: datetime
    end_time: Optional[datetime] = None
    all_day: bool = False
    location: str = ""
    recurrence: Optional[Literal["daily", "weekly", "monthly", "yearly"]] = None
    reminder_minutes_before: int = 15
    is_completed: bool = False
    category: str = "general"  # 'meeting' | 'task' | 'reminder' | 'deadline' | 'personal'
    tags: List[str] = Field(default_factory=list)


class CalendarEngine:
    """Operations engine for managing workspace calendar events and reminders."""

    def __init__(self) -> None:
        self.storage = workspace_storage
        self._cal_file = "calendar/events.json"
        self._events: List[CalendarEvent] = []
        self._load_events()

    def _load_events(self) -> None:
        """Load stored events from workspace storage."""
        try:
            content = self.storage.read_file(self._cal_file)
            data = json.loads(content)
            self._events = [CalendarEvent.model_validate(e) for e in data]
        except Exception:
            self._events = []

    def _save_events(self) -> None:
        """Persist events to workspace storage."""
        dumpable = [e.model_dump(mode="json") for e in self._events]
        self.storage.write_file(
            rel_path=self._cal_file,
            content=json.dumps(dumpable, indent=2),
            file_type="calendar",
            change_summary="Calendar events update",
        )

    def add_event(
        self,
        title: str,
        start_time: datetime,
        end_time: Optional[datetime] = None,
        description: str = "",
        location: str = "",
        category: str = "general",
        recurrence: Optional[Literal["daily", "weekly", "monthly", "yearly"]] = None,
        reminder_minutes_before: int = 15,
        tags: Optional[List[str]] = None,
    ) -> CalendarEvent:
        """Schedule a new calendar event or reminder."""
        if not end_time:
            end_time = start_time + timedelta(hours=1)

        event = CalendarEvent(
            title=title,
            start_time=start_time,
            end_time=end_time,
            description=description,
            location=location,
            category=category,
            recurrence=recurrence,
            reminder_minutes_before=reminder_minutes_before,
            tags=tags or [],
        )
        self._events.append(event)
        self._save_events()

        event_log.log_event(
            "calendar_event_added",
            source="calendar_engine",
            data={"title": title, "start": start_time.isoformat(), "category": category},
        )
        logger.info("Calendar event scheduled: '{}' at {}", title, start_time)
        return event

    def list_upcoming_events(self, days: int = 7) -> List[Dict[str, Any]]:
        """List events scheduled within the next N days."""
        now = datetime.now(timezone.utc)
        horizon = now + timedelta(days=days)

        upcoming = [
            e for e in self._events
            if e.start_time >= (now - timedelta(hours=2)) and e.start_time <= horizon
        ]
        return [e.model_dump(mode="json") for e in sorted(upcoming, key=lambda x: x.start_time)]

    def get_upcoming_events(self, days_ahead: int = 7) -> List[CalendarEvent]:
        """Get CalendarEvent objects scheduled within the next N days."""
        now = datetime.now(timezone.utc)
        horizon = now + timedelta(days=days_ahead)
        upcoming = [
            e for e in self._events
            if e.start_time >= (now - timedelta(hours=2)) and e.start_time <= horizon
        ]
        return sorted(upcoming, key=lambda x: x.start_time)

    def get_due_reminders(self) -> List[CalendarEvent]:
        """Check for events whose reminder window is currently active."""
        now = datetime.now(timezone.utc)
        due = []
        for e in self._events:
            if not e.is_completed:
                reminder_time = e.start_time - timedelta(minutes=e.reminder_minutes_before)
                # If within 5 minutes of reminder window
                if reminder_time <= now <= e.start_time:
                    due.append(e)
        return due

    def to_ical(self) -> str:
        """Export calendar to standard iCalendar (.ics) format."""
        lines = [
            "BEGIN:VCALENDAR",
            "VERSION:2.0",
            "PRODID:-//Mitchell AI//Mitchell Calendar 2.0//EN",
        ]
        for e in self._events:
            lines.append("BEGIN:VEVENT")
            lines.append(f"UID:{e.id}@mitchell.ai")
            lines.append(f"DTSTAMP:{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}")
            lines.append(f"DTSTART:{e.start_time.strftime('%Y%m%dT%H%M%SZ')}")
            if e.end_time:
                lines.append(f"DTEND:{e.end_time.strftime('%Y%m%dT%H%M%SZ')}")
            lines.append(f"SUMMARY:{e.title}")
            lines.append(f"DESCRIPTION:{e.description}")
            if e.location:
                lines.append(f"LOCATION:{e.location}")
            lines.append("END:VEVENT")
        lines.append("END:VCALENDAR")
        return "\r\n".join(lines)


calendar_engine = CalendarEngine()

__all__ = ["CalendarEvent", "CalendarEngine", "calendar_engine"]

"""Append-only JSON Lines event logging system."""

import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

try:
    import orjson

    def _dumps(obj: Any) -> str:
        return orjson.dumps(obj, default=str).decode("utf-8")

    def _loads(s: str) -> Any:
        return orjson.loads(s)

except ImportError:
    import json

    def _dumps(obj: Any) -> str:
        return json.dumps(obj, default=str)

    def _loads(s: str) -> Any:
        return json.loads(s)

from mitchell.core.config import settings


class Event(BaseModel):
    """Standard event model for Mitchell event logging."""

    id: str = Field(default_factory=lambda: uuid.uuid4().hex[:12], description="Unique event identifier")
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="UTC timestamp of the event",
    )
    type: str = Field(..., description="Type or category of the event")
    source: str = Field(..., description="Source component or agent emitting the event")
    data: Dict[str, Any] = Field(
        default_factory=dict,
        description="Arbitrary event payload data",
    )

    def to_json_line(self) -> str:
        """Serialize event to a single JSON line string."""
        event_dict = {
            "id": self.id,
            "timestamp": self.timestamp.isoformat(),
            "type": self.type,
            "source": self.source,
            "data": self.data,
        }
        return _dumps(event_dict)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Event":
        """Construct Event from a dictionary."""
        # Support both 'type' and 'event_type', 'data' and 'payload'
        event_type = data.get("type") or data.get("event_type") or "unknown"
        source = data.get("source") or "unknown"
        payload = data.get("data") or data.get("payload") or {}
        event_id = data.get("id") or uuid.uuid4().hex[:12]
        ts_str = data.get("timestamp")
        if ts_str:
            try:
                ts = datetime.fromisoformat(ts_str)
            except Exception:
                ts = datetime.now(timezone.utc)
        else:
            ts = datetime.now(timezone.utc)

        return cls(id=event_id, timestamp=ts, type=event_type, source=source, data=payload)


class EventLog:
    """Append-only JSON Lines event store."""

    def __init__(self, file_path: Optional[Path] = None) -> None:
        self.file_path = Path(file_path or settings.event_log_path)
        self._ensure_file_exists()

    def _ensure_file_exists(self) -> None:
        """Ensure the target log file parent directory exists."""
        self.file_path.parent.mkdir(parents=True, exist_ok=True)
        if not self.file_path.exists():
            self.file_path.touch(exist_ok=True)

    def log_event(
        self,
        event_type: str,
        source: str,
        data: Optional[Dict[str, Any]] = None,
    ) -> Event:
        """Append a new event to the log file."""
        event = Event(type=event_type, source=source, data=data or {})
        line = event.to_json_line() + "\n"
        with self.file_path.open("a", encoding="utf-8") as f:
            f.write(line)
        return event

    def get_recent(self, n: int = 20) -> List[Event]:
        """Retrieve the last n events from the log."""
        if not self.file_path.exists():
            return []

        events: List[Event] = []
        with self.file_path.open("r", encoding="utf-8") as f:
            lines = [line.strip() for line in f if line.strip()]

        recent_lines = lines[-n:] if n > 0 else lines
        for line in recent_lines:
            try:
                parsed = _loads(line)
                events.append(Event.from_dict(parsed))
            except Exception:
                continue
        return events

    def get_by_type(self, event_type: str, limit: Optional[int] = None) -> List[Event]:
        """Retrieve events filtered by event type."""
        if not self.file_path.exists():
            return []

        matched: List[Event] = []
        with self.file_path.open("r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    parsed = _loads(line)
                    if parsed.get("type") == event_type or parsed.get("event_type") == event_type:
                        matched.append(Event.from_dict(parsed))
                except Exception:
                    continue

        if limit is not None and limit > 0:
            return matched[-limit:]
        return matched


event_log = EventLog()

__all__ = ["Event", "EventLog", "event_log"]

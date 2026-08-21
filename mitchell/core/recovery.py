"""Checkpoint creation and Event Log state recovery engine."""

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Set
from pydantic import BaseModel, Field

from mitchell.core.config import settings
from mitchell.core.event_log import Event, event_log
from mitchell.core.logging import logger


class Checkpoint(BaseModel):
    """Snapshot of system runtime state at a point in time."""

    checkpoint_id: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    state_data: Dict[str, Any] = Field(default_factory=dict)
    last_event_timestamp: Optional[str] = None


class RecoveryEngine:
    """Manages state replay and crash recovery from the append-only Event Log."""

    def __init__(self) -> None:
        self.checkpoint_file = Path(settings.data_dir) / "checkpoints.jsonl"
        self.event_log = event_log

    def create_checkpoint(self, state_data: Dict[str, Any]) -> Checkpoint:
        """Create and persist a state snapshot checkpoint."""
        checkpoint_id = f"chk_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}"
        recent_events = self.event_log.get_recent(1)
        last_ts = recent_events[0].timestamp.isoformat() if recent_events else None

        chk = Checkpoint(
            checkpoint_id=checkpoint_id,
            state_data=state_data,
            last_event_timestamp=last_ts,
        )

        self.checkpoint_file.parent.mkdir(parents=True, exist_ok=True)
        with self.checkpoint_file.open("a", encoding="utf-8") as f:
            f.write(chk.model_dump_json() + "\n")

        logger.info("Checkpoint created: {}", checkpoint_id)
        self.event_log.log_event(
            "checkpoint_created",
            source="recovery_engine",
            data={"checkpoint_id": checkpoint_id},
        )
        return chk

    def get_latest_checkpoint(self) -> Optional[Checkpoint]:
        """Retrieve the most recent checkpoint."""
        if not self.checkpoint_file.exists():
            return None
        try:
            with self.checkpoint_file.open("r", encoding="utf-8") as f:
                lines = [line.strip() for line in f if line.strip()]
                if not lines:
                    return None
                data = json.loads(lines[-1])
                return Checkpoint.model_validate(data)
        except Exception as e:
            logger.error("Failed to read latest checkpoint: {}", e)
            return None

    def audit_and_recover(self) -> Dict[str, Any]:
        """Inspect recent Event Log entries for interrupted operations and generate recovery plan."""
        recent_events = self.event_log.get_recent(50)
        started_tasks: Dict[str, Event] = {}
        completed_tasks: Set[str] = set()

        for ev in recent_events:
            if ev.type.endswith("_started"):
                action = ev.data.get("action") or ev.data.get("skill_name") or ev.type
                started_tasks[action] = ev
            elif ev.type.endswith("_finished") or ev.type.endswith("_completed"):
                action = ev.data.get("action") or ev.data.get("skill_name") or ev.type
                completed_tasks.add(action)

        uncompleted = [act for act in started_tasks if act not in completed_tasks]

        logger.info("Recovery Audit: Found {} uncompleted tasks from previous session", len(uncompleted))

        return {
            "status": "healthy" if not uncompleted else "uncompleted_tasks_detected",
            "uncompleted_tasks": uncompleted,
            "total_recent_events_scanned": len(recent_events),
            "latest_checkpoint": self.get_latest_checkpoint().checkpoint_id if self.get_latest_checkpoint() else "None",
        }


recovery_engine = RecoveryEngine()

__all__ = ["Checkpoint", "RecoveryEngine", "recovery_engine"]

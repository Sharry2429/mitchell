"""Checkpoint creation, Event Log state recovery, and novel failure handling engine.

Enhanced for Peak spec with:
- Novel failure pattern detection and categorization
- Self-diagnostic reports
- Offline resilience indicators
- Automatic self-repair suggestions
- Failure pattern memory (learns from past failures to prevent recurrence)
"""

import json
import traceback
from collections import Counter
from datetime import datetime, timezone, timedelta
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


class FailurePattern(BaseModel):
    """A detected failure pattern with frequency and suggested remediation."""

    pattern_id: str
    error_type: str
    error_message_template: str = ""
    occurrence_count: int = 1
    first_seen: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    last_seen: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    affected_components: List[str] = Field(default_factory=list)
    suggested_fix: str = ""
    is_novel: bool = True
    auto_resolved: bool = False


class DiagnosticReport(BaseModel):
    """System health diagnostic report."""

    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    overall_health: str = "healthy"  # healthy, degraded, critical
    uptime_seconds: float = 0.0
    subsystem_status: Dict[str, str] = Field(default_factory=dict)
    active_issues: List[str] = Field(default_factory=list)
    failure_patterns: List[FailurePattern] = Field(default_factory=list)
    offline_capable: Dict[str, bool] = Field(default_factory=dict)
    recovery_suggestions: List[str] = Field(default_factory=list)


class RecoveryEngine:
    """Manages state replay, crash recovery, novel failure detection, and self-diagnostics.

    Enhanced with pattern-based failure analysis, self-repair suggestions,
    and offline resilience tracking.
    """

    def __init__(self) -> None:
        self.checkpoint_file = Path(settings.data_dir) / "checkpoints.jsonl"
        self.failure_log_file = Path(settings.data_dir) / "failure_patterns.json"
        self.event_log = event_log
        self._failure_patterns: Dict[str, FailurePattern] = {}
        self._start_time = datetime.now(timezone.utc)
        self._load_failure_patterns()

    def _load_failure_patterns(self) -> None:
        """Load known failure patterns from disk."""
        if self.failure_log_file.exists():
            try:
                with self.failure_log_file.open("r", encoding="utf-8") as f:
                    data = json.load(f)
                    for pid, pdata in data.items():
                        self._failure_patterns[pid] = FailurePattern.model_validate(pdata)
            except Exception as e:
                logger.warning("Failed to load failure patterns: {}", e)

    def _save_failure_patterns(self) -> None:
        """Persist failure patterns to disk."""
        try:
            self.failure_log_file.parent.mkdir(parents=True, exist_ok=True)
            with self.failure_log_file.open("w", encoding="utf-8") as f:
                data = {pid: p.model_dump(mode="json") for pid, p in self._failure_patterns.items()}
                json.dump(data, f, indent=2)
        except Exception as e:
            logger.error("Failed to save failure patterns: {}", e)

    # ── Checkpoints ────────────────────────────────────────────────────────

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

    # ── Novel Failure Handling ─────────────────────────────────────────────

    def record_failure(
        self,
        error: Exception,
        component: str = "unknown",
        context: Optional[Dict[str, Any]] = None,
    ) -> FailurePattern:
        """Record a failure, detect if it's novel, and suggest remediation."""
        error_type = type(error).__name__
        error_msg = str(error)[:200]
        pattern_id = f"{error_type}:{component}"

        if pattern_id in self._failure_patterns:
            # Known pattern — update frequency
            pattern = self._failure_patterns[pattern_id]
            pattern.occurrence_count += 1
            pattern.last_seen = datetime.now(timezone.utc)
            pattern.is_novel = False
            if component not in pattern.affected_components:
                pattern.affected_components.append(component)
        else:
            # Novel failure — create new pattern
            pattern = FailurePattern(
                pattern_id=pattern_id,
                error_type=error_type,
                error_message_template=error_msg,
                affected_components=[component],
                suggested_fix=self._suggest_fix(error_type, error_msg, component),
                is_novel=True,
            )
            self._failure_patterns[pattern_id] = pattern

            logger.warning(
                "Novel failure detected: {} in {} — {}",
                error_type, component, error_msg,
            )
            self.event_log.log_event(
                "novel_failure_detected",
                source="recovery_engine",
                data={
                    "error_type": error_type,
                    "component": component,
                    "message": error_msg,
                    "suggested_fix": pattern.suggested_fix,
                },
            )

        self._save_failure_patterns()
        return pattern

    def _suggest_fix(self, error_type: str, error_msg: str, component: str) -> str:
        """Generate auto-repair suggestions based on error type."""
        suggestions = {
            "ConnectionError": "Check network connectivity. Retry with exponential backoff.",
            "TimeoutError": "Increase timeout settings or try a different provider.",
            "PermissionError": "Check file/system permissions. Run with elevated privileges if needed.",
            "FileNotFoundError": "Verify file path exists. Check working directory.",
            "ImportError": "Install missing dependency. Run 'pip install <package>'.",
            "ModuleNotFoundError": "Install missing module. Check virtual environment activation.",
            "JSONDecodeError": "Response was not valid JSON. Check API endpoint and payload.",
            "KeyError": "Expected key missing from data. Validate input schema.",
            "ValueError": "Invalid value provided. Check parameter constraints.",
            "RuntimeError": "Runtime condition failed. Check system state and resources.",
            "OSError": "OS-level error. Check disk space, file handles, and system resources.",
            "sqlite3.OperationalError": "Database locked or corrupted. Try closing other connections.",
        }

        for known_type, suggestion in suggestions.items():
            if known_type in error_type:
                return suggestion

        # Analyze error message for common patterns
        msg_lower = error_msg.lower()
        if "rate limit" in msg_lower or "429" in msg_lower:
            return "Rate limit hit. Switch to a different provider or wait before retrying."
        if "api key" in msg_lower or "unauthorized" in msg_lower or "401" in msg_lower:
            return "Authentication failed. Check API key configuration."
        if "not found" in msg_lower or "404" in msg_lower:
            return "Resource not found. Verify URL/endpoint and parameters."
        if "memory" in msg_lower or "oom" in msg_lower:
            return "Memory exhaustion. Reduce batch size or free system memory."

        return f"Unknown error in {component}. Collect logs and investigate manually."

    def get_failure_summary(self) -> Dict[str, Any]:
        """Get summary of all recorded failure patterns."""
        novel = [p for p in self._failure_patterns.values() if p.is_novel]
        recurring = [p for p in self._failure_patterns.values() if not p.is_novel and p.occurrence_count >= 3]

        return {
            "total_patterns": len(self._failure_patterns),
            "novel_failures": len(novel),
            "recurring_failures": len(recurring),
            "top_failures": [
                {
                    "pattern_id": p.pattern_id,
                    "error_type": p.error_type,
                    "count": p.occurrence_count,
                    "components": p.affected_components,
                    "suggested_fix": p.suggested_fix,
                }
                for p in sorted(
                    self._failure_patterns.values(),
                    key=lambda x: x.occurrence_count,
                    reverse=True,
                )[:10]
            ],
        }

    # ── Self-Diagnostics ───────────────────────────────────────────────────

    def run_diagnostics(self) -> DiagnosticReport:
        """Run a comprehensive self-diagnostic check."""
        uptime = (datetime.now(timezone.utc) - self._start_time).total_seconds()

        # Check subsystem health
        subsystems: Dict[str, str] = {}
        issues: List[str] = []
        suggestions: List[str] = []

        # Core subsystems
        subsystems["event_log"] = self._check_subsystem("event_log")
        subsystems["memory_db"] = self._check_subsystem("memory_db")
        subsystems["cost_tracker"] = self._check_subsystem("cost_tracker")
        subsystems["tool_registry"] = self._check_subsystem("tool_registry")

        # Check for recurring failures
        failure_summary = self.get_failure_summary()
        if failure_summary["recurring_failures"] > 0:
            issues.append(f"{failure_summary['recurring_failures']} recurring failure patterns detected")
            for fp in failure_summary["top_failures"][:3]:
                suggestions.append(f"Fix {fp['error_type']} in {fp['components']}: {fp['suggested_fix']}")

        # Determine overall health
        unhealthy_count = sum(1 for v in subsystems.values() if v != "healthy")
        if unhealthy_count == 0 and not issues:
            overall = "healthy"
        elif unhealthy_count <= 2:
            overall = "degraded"
        else:
            overall = "critical"

        # Offline capability check
        offline = {
            "core_engine": True,
            "memory": True,
            "file_operations": True,
            "tool_execution": True,
            "llm_inference": False,  # Requires API
            "browser_automation": True,
            "voice_stt": False,  # Requires API (unless local whisper)
            "voice_tts": True,  # System TTS works offline
        }

        report = DiagnosticReport(
            overall_health=overall,
            uptime_seconds=round(uptime, 1),
            subsystem_status=subsystems,
            active_issues=issues,
            failure_patterns=[p for p in self._failure_patterns.values() if p.occurrence_count >= 2],
            offline_capable=offline,
            recovery_suggestions=suggestions,
        )

        self.event_log.log_event(
            "diagnostics_completed",
            source="recovery_engine",
            data={"overall_health": overall, "issues": len(issues)},
        )

        return report

    def _check_subsystem(self, name: str) -> str:
        """Quick health check for a named subsystem."""
        try:
            if name == "event_log":
                self.event_log.get_recent(1)
            elif name == "memory_db":
                from mitchell.memory.database import memory_db
                memory_db._get_connection().close()
            elif name == "cost_tracker":
                from mitchell.core.cost import cost_tracker
                cost_tracker.get_summary()
            elif name == "tool_registry":
                from mitchell.tools.registry import tool_registry
                tool_registry.list_tools()
            return "healthy"
        except Exception as e:
            logger.warning("Subsystem '{}' health check failed: {}", name, e)
            return f"unhealthy: {e}"

    # ── Auto Self-Repair ───────────────────────────────────────────────────

    def attempt_self_repair(self, pattern_id: str) -> Dict[str, Any]:
        """Attempt automatic repair for a known failure pattern."""
        pattern = self._failure_patterns.get(pattern_id)
        if not pattern:
            return {"status": "unknown_pattern", "repaired": False}

        repair_actions: Dict[str, str] = {
            "sqlite3.OperationalError": "database_repair",
            "ConnectionError": "retry_with_backoff",
            "FileNotFoundError": "recreate_missing_paths",
        }

        action = None
        for error_key, repair in repair_actions.items():
            if error_key in pattern.error_type:
                action = repair
                break

        if action == "recreate_missing_paths":
            # Ensure all data directories exist
            settings.data_dir.mkdir(parents=True, exist_ok=True)
            settings.workspace_root.mkdir(parents=True, exist_ok=True)
            settings.download_dir.mkdir(parents=True, exist_ok=True)
            pattern.auto_resolved = True
            self._save_failure_patterns()
            return {"status": "repaired", "action": "recreated_directories", "repaired": True}

        if action == "database_repair":
            try:
                from mitchell.memory.database import memory_db
                memory_db._ensure_tables()
                pattern.auto_resolved = True
                self._save_failure_patterns()
                return {"status": "repaired", "action": "rebuilt_tables", "repaired": True}
            except Exception as e:
                return {"status": "repair_failed", "error": str(e), "repaired": False}

        return {"status": "no_auto_repair_available", "suggested_fix": pattern.suggested_fix, "repaired": False}


recovery_engine = RecoveryEngine()

__all__ = [
    "Checkpoint", "RecoveryEngine", "recovery_engine",
    "FailurePattern", "DiagnosticReport",
]

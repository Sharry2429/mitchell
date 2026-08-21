"""Self-Model tier tracking Mitchell's capabilities, success rates, latency, and gaps."""

import json
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from mitchell.core.event_log import event_log
from mitchell.core.logging import logger
from mitchell.memory.database import memory_db


class CapabilityStats(BaseModel):
    """Statistical model of a verified Mitchell capability."""

    capability_name: str = Field(..., description="Unique capability or tool name")
    category: str = Field(default="general", description="Domain: browser | windows | android | skill | core")
    total_runs: int = Field(default=0, description="Total execution count")
    successes: int = Field(default=0, description="Successful executions")
    failures: int = Field(default=0, description="Failed executions")
    avg_duration_s: float = Field(default=0.0, description="Average runtime in seconds")
    avg_tokens: int = Field(default=0, description="Average token consumption")
    confidence: float = Field(default=0.5, description="Calibrated confidence score (0.0 - 1.0)")
    known_gaps: List[str] = Field(default_factory=list, description="Known failure edge cases / missing features")
    preferred_strategy: str = Field(default="direct", description="Optimal execution strategy")

    @property
    def success_rate(self) -> float:
        """Calculate dynamic success percentage."""
        if self.total_runs == 0:
            return 1.0
        return round((self.successes / self.total_runs) * 100, 1)


class SelfModel:
    """Maintains an introspective self-model of Mitchell's performance and limitations."""

    def __init__(self) -> None:
        self.db = memory_db
        self._initialize_baseline_capabilities()

    def _initialize_baseline_capabilities(self) -> None:
        """Seed core pillar capabilities if not already present."""
        baselines = [
            ("browser_automation", "browser", 0.9, "playwright_human_mouse"),
            ("windows_desktop_control", "windows", 0.85, "pywinauto_uia"),
            ("android_wireless_control", "android", 0.85, "wireless_adb"),
            ("fast_intent_routing", "core", 0.95, "rule_based"),
            ("skill_execution", "skill", 0.8, "step_by_step_runner"),
        ]
        for name, cat, conf, strat in baselines:
            if not self.get_capability(name):
                self._upsert(CapabilityStats(
                    capability_name=name,
                    category=cat,
                    confidence=conf,
                    preferred_strategy=strat,
                ))

    def _upsert(self, cap: CapabilityStats) -> None:
        with self.db._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO self_model (
                    capability_name, category, total_runs, successes, failures,
                    avg_duration_s, avg_tokens, confidence, known_gaps, preferred_strategy, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                ON CONFLICT(capability_name) DO UPDATE SET
                    category = excluded.category,
                    total_runs = excluded.total_runs,
                    successes = excluded.successes,
                    failures = excluded.failures,
                    avg_duration_s = excluded.avg_duration_s,
                    avg_tokens = excluded.avg_tokens,
                    confidence = excluded.confidence,
                    known_gaps = excluded.known_gaps,
                    preferred_strategy = excluded.preferred_strategy,
                    updated_at = CURRENT_TIMESTAMP
                """,
                (
                    cap.capability_name,
                    cap.category,
                    cap.total_runs,
                    cap.successes,
                    cap.failures,
                    cap.avg_duration_s,
                    cap.avg_tokens,
                    cap.confidence,
                    json.dumps(cap.known_gaps),
                    cap.preferred_strategy,
                ),
            )
            conn.commit()

    def record_run(
        self,
        capability_name: str,
        category: str = "general",
        success: bool = True,
        duration_s: float = 0.0,
        tokens_used: int = 0,
        gap: Optional[str] = None,
        strategy: Optional[str] = None,
    ) -> CapabilityStats:
        """Update capability stats following a job or tool execution."""
        cap = self.get_capability(capability_name) or CapabilityStats(
            capability_name=capability_name,
            category=category,
        )

        old_total = cap.total_runs
        cap.total_runs += 1
        if success:
            cap.successes += 1
        else:
            cap.failures += 1

        # Moving average duration and tokens
        cap.avg_duration_s = round((cap.avg_duration_s * old_total + duration_s) / cap.total_runs, 2)
        cap.avg_tokens = int((cap.avg_tokens * old_total + tokens_used) / cap.total_runs)

        # Calibrated confidence adjustment
        ratio = cap.successes / cap.total_runs
        cap.confidence = round(0.3 + 0.7 * ratio, 2)

        if gap and gap not in cap.known_gaps:
            cap.known_gaps.append(gap)
        if strategy:
            cap.preferred_strategy = strategy

        self._upsert(cap)

        logger.debug("Self-Model updated: {} (Success Rate: {}%, Confidence: {})", capability_name, cap.success_rate, cap.confidence)
        event_log.log_event(
            "self_model_updated",
            source="self_model",
            data={
                "capability": capability_name,
                "success_rate": cap.success_rate,
                "total_runs": cap.total_runs,
            },
        )
        return cap

    def get_capability(self, capability_name: str) -> Optional[CapabilityStats]:
        """Retrieve capability statistics."""
        with self.db._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM self_model WHERE capability_name = ?", (capability_name,))
            row = cursor.fetchone()
            if not row:
                return None

            return CapabilityStats(
                capability_name=row["capability_name"],
                category=row["category"],
                total_runs=row["total_runs"],
                successes=row["successes"],
                failures=row["failures"],
                avg_duration_s=row["avg_duration_s"],
                avg_tokens=row["avg_tokens"],
                confidence=row["confidence"],
                known_gaps=json.loads(row["known_gaps"] or "[]"),
                preferred_strategy=row["preferred_strategy"] or "direct",
            )

    def list_all(self) -> List[CapabilityStats]:
        """List all capabilities in the self-model."""
        with self.db._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM self_model ORDER BY category, capability_name")
            rows = cursor.fetchall()

        return [
            CapabilityStats(
                capability_name=row["capability_name"],
                category=row["category"],
                total_runs=row["total_runs"],
                successes=row["successes"],
                failures=row["failures"],
                avg_duration_s=row["avg_duration_s"],
                avg_tokens=row["avg_tokens"],
                confidence=row["confidence"],
                known_gaps=json.loads(row["known_gaps"] or "[]"),
                preferred_strategy=row["preferred_strategy"] or "direct",
            )
            for row in rows
        ]


self_model = SelfModel()

__all__ = ["CapabilityStats", "SelfModel", "self_model"]

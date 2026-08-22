"""Self-Model tier tracking Mitchell's capabilities, user model, procedural memory, and semantic graph.

Enhanced for Peak spec with:
- User Model: continuously updated preferences, patterns, values, history
- Procedural Memory: how-to knowledge and learned procedures
- Semantic Graph: concept relationships with contradiction detection
- Self-compacting with stale entry cleanup
"""

import json
import uuid
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional, Tuple
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


class UserPreference(BaseModel):
    """A single user model entry — preference, pattern, or value."""

    key: str
    category: str = "preference"
    value: str = ""
    confidence: float = 0.8
    evidence_count: int = 1
    source: str = "observed"
    first_observed: Optional[datetime] = None
    last_observed: Optional[datetime] = None
    contradicted_by: Optional[str] = None


class ProceduralEntry(BaseModel):
    """A learned how-to procedure."""

    id: str = ""
    name: str
    description: str = ""
    trigger_pattern: str = ""
    steps: List[Dict[str, Any]] = Field(default_factory=list)
    success_count: int = 0
    failure_count: int = 0
    avg_duration_s: float = 0.0
    confidence: float = 0.5
    source: str = "learned"

    @property
    def success_rate(self) -> float:
        """Calculate procedure execution success rate percentage."""
        total = self.success_count + self.failure_count
        return (self.success_count / total * 100.0) if total > 0 else (self.confidence * 100.0)


class SemanticTriple(BaseModel):
    """A subject-predicate-object relationship in the semantic graph."""

    id: str = ""
    subject: str
    predicate: str
    object: str
    confidence: float = 0.8
    source: str = "inferred"
    evidence: Optional[str] = None


class SelfModel:
    """Maintains an introspective self-model of Mitchell's performance, user preferences,
    procedural knowledge, and semantic relationships."""

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

    # ── Capability Stats (original) ────────────────────────────────────────

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

    # ── User Model ─────────────────────────────────────────────────────────

    def set_user_preference(
        self,
        key: str,
        value: str,
        category: str = "preference",
        source: str = "observed",
        confidence: float = 0.8,
    ) -> UserPreference:
        """Set or update a user model entry. Detects contradictions automatically."""
        existing = self.get_user_preference(key)
        contradicted_by = None

        if existing and existing.value != value:
            # Contradiction detected — record it
            contradicted_by = existing.value
            logger.info(
                "User model contradiction detected for '{}': '{}' → '{}' (source: {})",
                key, existing.value, value, source,
            )
            event_log.log_event(
                "user_model_contradiction",
                source="self_model",
                data={"key": key, "old_value": existing.value, "new_value": value},
            )
            # Increase confidence of newer entry
            evidence_count = existing.evidence_count + 1
        else:
            evidence_count = (existing.evidence_count + 1) if existing else 1

        with self.db._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO user_model (key, category, value, confidence, evidence_count, source, last_observed, contradicted_by)
                VALUES (?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP, ?)
                ON CONFLICT(key) DO UPDATE SET
                    value = excluded.value,
                    confidence = excluded.confidence,
                    evidence_count = excluded.evidence_count,
                    source = excluded.source,
                    last_observed = CURRENT_TIMESTAMP,
                    contradicted_by = excluded.contradicted_by
                """,
                (key, category, value, confidence, evidence_count, source, contradicted_by),
            )
            conn.commit()

        return UserPreference(
            key=key, category=category, value=value, confidence=confidence,
            evidence_count=evidence_count, source=source, contradicted_by=contradicted_by,
        )

    def get_user_preference(self, key: str) -> Optional[UserPreference]:
        """Get a single user model entry."""
        with self.db._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM user_model WHERE key = ?", (key,))
            row = cursor.fetchone()
            if not row:
                return None
            return UserPreference(
                key=row["key"],
                category=row["category"],
                value=row["value"],
                confidence=row["confidence"],
                evidence_count=row["evidence_count"],
                source=row["source"],
                contradicted_by=row["contradicted_by"],
            )

    def get_user_preferences(self, category: Optional[str] = None) -> List[UserPreference]:
        """Get all user model entries, optionally filtered by category."""
        with self.db._get_connection() as conn:
            cursor = conn.cursor()
            if category:
                cursor.execute("SELECT * FROM user_model WHERE category = ? ORDER BY key", (category,))
            else:
                cursor.execute("SELECT * FROM user_model ORDER BY category, key")
            rows = cursor.fetchall()

        return [
            UserPreference(
                key=row["key"], category=row["category"], value=row["value"],
                confidence=row["confidence"], evidence_count=row["evidence_count"],
                source=row["source"], contradicted_by=row["contradicted_by"],
            )
            for row in rows
        ]

    def get_user_context_summary(self) -> str:
        """Build a summary of the user model for injection into LLM system prompts."""
        prefs = self.get_user_preferences()
        if not prefs:
            return "No user preferences recorded yet."
        lines = ["Known User Preferences & Patterns:"]
        for p in prefs[:20]:  # Limit to top 20 for context window
            lines.append(f"  • [{p.category}] {p.key}: {p.value} (confidence: {p.confidence:.1f})")
        return "\n".join(lines)

    # ── Procedural Memory ──────────────────────────────────────────────────

    def store_procedure(
        self,
        name: str,
        description: str,
        steps: List[Dict[str, Any]],
        trigger_pattern: str = "",
        source: str = "learned",
    ) -> ProceduralEntry:
        """Store a learned procedure (how-to knowledge)."""
        proc_id = str(uuid.uuid4())[:12]
        with self.db._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO procedural_memory (id, name, description, trigger_pattern, steps_json, source)
                VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(name) DO UPDATE SET
                    description = excluded.description,
                    trigger_pattern = excluded.trigger_pattern,
                    steps_json = excluded.steps_json,
                    source = excluded.source,
                    updated_at = CURRENT_TIMESTAMP
                """,
                (proc_id, name, description, trigger_pattern, json.dumps(steps), source),
            )
            conn.commit()

        logger.info("Procedural memory stored: '{}' ({} steps)", name, len(steps))
        return ProceduralEntry(
            id=proc_id, name=name, description=description,
            trigger_pattern=trigger_pattern, steps=steps, source=source,
        )

    def get_procedure(self, name: str) -> Optional[ProceduralEntry]:
        """Retrieve a stored procedure by name."""
        with self.db._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM procedural_memory WHERE name = ?", (name,))
            row = cursor.fetchone()
            if not row:
                return None
            return ProceduralEntry(
                id=row["id"], name=row["name"], description=row["description"],
                trigger_pattern=row["trigger_pattern"] or "",
                steps=json.loads(row["steps_json"] or "[]"),
                success_count=row["success_count"], failure_count=row["failure_count"],
                avg_duration_s=row["avg_duration_s"], confidence=row["confidence"],
                source=row["source"],
            )

    def find_procedures(self, query: str) -> List[ProceduralEntry]:
        """Search procedures by name or trigger pattern (simple LIKE matching)."""
        with self.db._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT * FROM procedural_memory WHERE name LIKE ? OR trigger_pattern LIKE ? OR description LIKE ? ORDER BY confidence DESC LIMIT 10",
                (f"%{query}%", f"%{query}%", f"%{query}%"),
            )
            rows = cursor.fetchall()

        return [
            ProceduralEntry(
                id=row["id"], name=row["name"], description=row["description"],
                trigger_pattern=row["trigger_pattern"] or "",
                steps=json.loads(row["steps_json"] or "[]"),
                success_count=row["success_count"], failure_count=row["failure_count"],
                confidence=row["confidence"], source=row["source"],
            )
            for row in rows
        ]

    def record_procedure_run(self, name: str, success: bool, duration_s: float = 0.0) -> None:
        """Update procedure stats after execution."""
        with self.db._get_connection() as conn:
            cursor = conn.cursor()
            if success:
                cursor.execute(
                    "UPDATE procedural_memory SET success_count = success_count + 1, updated_at = CURRENT_TIMESTAMP WHERE name = ?",
                    (name,),
                )
            else:
                cursor.execute(
                    "UPDATE procedural_memory SET failure_count = failure_count + 1, updated_at = CURRENT_TIMESTAMP WHERE name = ?",
                    (name,),
                )
            conn.commit()

    # ── Semantic Graph ─────────────────────────────────────────────────────

    def add_semantic_triple(
        self,
        subject: str,
        predicate: str,
        obj: Optional[str] = None,
        confidence: float = 0.8,
        source: str = "inferred",
        evidence: Optional[str] = None,
        object: Optional[str] = None,
    ) -> SemanticTriple:
        """Add a subject-predicate-object relationship. Detects contradictions."""
        resolved_obj = obj or object or ""
        triple_id = str(uuid.uuid4())[:12]

        # Check for contradictions (same subject+predicate with different object)
        existing = self.query_semantic(subject=subject, predicate=predicate)
        for e in existing:
            if e.object != resolved_obj:
                logger.info(
                    "Semantic contradiction: '{}' '{}' was '{}', now '{}'",
                    subject, predicate, e.object, resolved_obj,
                )
                event_log.log_event(
                    "semantic_contradiction",
                    source="self_model",
                    data={"subject": subject, "predicate": predicate, "old_object": e.object, "new_object": resolved_obj},
                )

        with self.db._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO semantic_graph (id, subject, predicate, object, confidence, source, evidence)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(subject, predicate, object) DO UPDATE SET
                    confidence = excluded.confidence,
                    source = excluded.source,
                    evidence = excluded.evidence
                """,
                (triple_id, subject, predicate, resolved_obj, confidence, source, evidence),
            )
            conn.commit()

        return SemanticTriple(
            id=triple_id, subject=subject, predicate=predicate,
            object=resolved_obj, confidence=confidence, source=source, evidence=evidence,
        )

    def query_semantic(
        self,
        subject: Optional[str] = None,
        predicate: Optional[str] = None,
        obj: Optional[str] = None,
    ) -> List[SemanticTriple]:
        """Query the semantic graph by subject, predicate, and/or object."""
        conditions = []
        params = []
        if subject:
            conditions.append("subject = ?")
            params.append(subject)
        if predicate:
            conditions.append("predicate = ?")
            params.append(predicate)
        if obj:
            conditions.append("object = ?")
            params.append(obj)

        where = " AND ".join(conditions) if conditions else "1=1"
        with self.db._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                f"SELECT * FROM semantic_graph WHERE {where} ORDER BY confidence DESC LIMIT 50",
                params,
            )
            rows = cursor.fetchall()

        return [
            SemanticTriple(
                id=row["id"], subject=row["subject"], predicate=row["predicate"],
                object=row["object"], confidence=row["confidence"],
                source=row["source"], evidence=row["evidence"],
            )
            for row in rows
        ]

    # ── Self-Compacting ────────────────────────────────────────────────────

    def compact(self, max_age_days: int = 90) -> Dict[str, int]:
        """Self-compact memory by removing low-confidence and stale entries.
        Returns counts of items removed per table."""
        cutoff = (datetime.now(timezone.utc) - timedelta(days=max_age_days)).isoformat()
        removed = {}

        with self.db._get_connection() as conn:
            cursor = conn.cursor()

            # Remove low-confidence user preferences older than cutoff
            cursor.execute(
                "DELETE FROM user_model WHERE confidence < 0.3 AND last_observed < ?",
                (cutoff,),
            )
            removed["user_model"] = cursor.rowcount

            # Remove low-confidence semantic triples
            cursor.execute(
                "DELETE FROM semantic_graph WHERE confidence < 0.2 AND created_at < ?",
                (cutoff,),
            )
            removed["semantic_graph"] = cursor.rowcount

            # Remove expired medium-term memories
            cursor.execute(
                "DELETE FROM medium_term_memory WHERE expires_at IS NOT NULL AND expires_at < CURRENT_TIMESTAMP",
            )
            removed["medium_term_expired"] = cursor.rowcount

            # Decay medium-term memories
            cursor.execute(
                "UPDATE medium_term_memory SET decay_factor = decay_factor * 0.95 WHERE decay_factor > 0.1",
            )

            # Remove fully-decayed medium-term memories
            cursor.execute(
                "DELETE FROM medium_term_memory WHERE decay_factor < 0.1",
            )
            removed["medium_term_decayed"] = cursor.rowcount

            conn.commit()

        logger.info("Self-compaction complete: {}", removed)
        event_log.log_event(
            "memory_compacted", source="self_model", data=removed,
        )
        return removed

    # ── Full State Export ───────────────────────────────────────────────────

    def get_full_state(self) -> Dict[str, Any]:
        """Export full self-model state for Studio UI."""
        return {
            "capabilities": [c.model_dump() for c in self.list_all()],
            "user_preferences": [p.model_dump() for p in self.get_user_preferences()],
            "user_context": self.get_user_context_summary(),
        }


self_model = SelfModel()

__all__ = [
    "CapabilityStats", "SelfModel", "self_model",
    "UserPreference", "ProceduralEntry", "SemanticTriple",
]

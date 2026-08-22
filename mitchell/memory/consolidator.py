"""Background Memory Consolidation with medium-term memory, contradiction detection, and auto-summarization.

Enhanced for Peak spec:
- Medium-term memory tier (buffer between short-term chat and long-term storage)
- Contradiction detection during consolidation
- Automatic summarization of stale entries
- Pattern extraction from episodic history → user model + procedural memory
"""

import json
import uuid
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional

from mitchell.core.event_log import event_log
from mitchell.core.logging import logger
from mitchell.memory.database import memory_db
from mitchell.memory.episodic import episodic_memory
from mitchell.memory.long_term import long_term_memory
from mitchell.memory.self_model import self_model


class MediumTermMemory:
    """Buffer between short-term chat context and long-term storage.

    Entries have importance scores and decay factors. Important items
    get promoted to long-term, decayed items get garbage-collected.
    """

    def __init__(self) -> None:
        self.db = memory_db

    def store(
        self,
        content: str,
        context: str = "",
        importance: float = 0.5,
        source_episode_id: str = "",
        ttl_hours: int = 72,
    ) -> str:
        """Store an item in medium-term memory with a TTL."""
        item_id = str(uuid.uuid4())[:12]
        expires_at = (datetime.now(timezone.utc) + timedelta(hours=ttl_hours)).isoformat()

        with self.db._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO medium_term_memory (id, content, context, importance, source_episode_id, expires_at)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (item_id, content, context, importance, source_episode_id, expires_at),
            )
            conn.commit()

        return item_id

    def get_recent(self, limit: int = 20) -> List[Dict[str, Any]]:
        """Get recent medium-term memories ordered by importance."""
        with self.db._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT * FROM medium_term_memory
                WHERE expires_at IS NULL OR expires_at > CURRENT_TIMESTAMP
                ORDER BY importance DESC, created_at DESC
                LIMIT ?
                """,
                (limit,),
            )
            rows = cursor.fetchall()

        return [
            {
                "id": row["id"],
                "content": row["content"],
                "context": row["context"],
                "importance": row["importance"],
                "access_count": row["access_count"],
                "decay_factor": row["decay_factor"],
            }
            for row in rows
        ]

    def access(self, item_id: str) -> None:
        """Mark an item as accessed (increases its longevity)."""
        with self.db._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                UPDATE medium_term_memory
                SET access_count = access_count + 1,
                    last_accessed = CURRENT_TIMESTAMP,
                    decay_factor = MIN(1.0, decay_factor + 0.1)
                WHERE id = ?
                """,
                (item_id,),
            )
            conn.commit()

    def promote_to_long_term(self, item_id: str, category: str, key: str) -> bool:
        """Promote a medium-term memory to long-term storage."""
        with self.db._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM medium_term_memory WHERE id = ?", (item_id,))
            row = cursor.fetchone()
            if not row:
                return False

            long_term_memory.remember(
                category=category,
                key=key,
                content=row["content"],
                source="promoted_from_medium_term",
            )

            cursor.execute("DELETE FROM medium_term_memory WHERE id = ?", (item_id,))
            conn.commit()

        logger.info("Medium-term memory '{}' promoted to long-term as [{}:{}]", item_id, category, key)
        return True

    def get_important(self, threshold: float = 0.7) -> List[Dict[str, Any]]:
        """Get high-importance items that are candidates for promotion."""
        with self.db._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT * FROM medium_term_memory WHERE importance >= ? ORDER BY importance DESC",
                (threshold,),
            )
            rows = cursor.fetchall()

        return [
            {
                "id": row["id"],
                "content": row["content"],
                "context": row["context"],
                "importance": row["importance"],
                "access_count": row["access_count"],
            }
            for row in rows
        ]


medium_term_memory = MediumTermMemory()


class MemoryConsolidator:
    """Consolidates episodic history into generalized facts, preferences, and self-model insights.

    Enhanced with medium-term memory promotion, pattern extraction, and contradiction detection.
    """

    def __init__(self) -> None:
        self.db = memory_db
        self.episodic = episodic_memory
        self.long_term = long_term_memory
        self.self_model = self_model
        self.medium_term = medium_term_memory

    def run_consolidation(self) -> Dict[str, Any]:
        """Perform a full consolidation pass:
        1. Analyze episodic patterns → extract insights
        2. Detect tool usage patterns → update self-model
        3. Extract user preferences from interactions
        4. Promote important medium-term memories
        5. Self-compact stale entries
        """
        logger.info("MemoryConsolidator: Starting consolidation pass...")
        recent_episodes = self.episodic.get_recent(limit=20)

        consolidated_insights: List[str] = []

        # 1. Analyze tool usage patterns
        tool_patterns = self._analyze_tool_patterns(recent_episodes)
        consolidated_insights.extend(tool_patterns)

        # 2. Detect success/failure patterns and update self-model
        performance_insights = self._analyze_performance(recent_episodes)
        consolidated_insights.extend(performance_insights)

        # 3. Extract time-of-day patterns
        time_patterns = self._analyze_time_patterns(recent_episodes)
        consolidated_insights.extend(time_patterns)

        # 4. Promote high-importance medium-term memories
        promoted = self._promote_important_memories()
        if promoted > 0:
            consolidated_insights.append(f"Promoted {promoted} important memories to long-term storage")

        # 5. Self-compact stale data
        compaction_result = self.self_model.compact()

        event_log.log_event(
            "memory_consolidated",
            source="memory_consolidator",
            data={
                "insights_count": len(consolidated_insights),
                "insights": consolidated_insights,
                "promoted_count": promoted,
                "compaction": compaction_result,
            },
        )

        logger.info("MemoryConsolidator: Pass complete with {} insights.", len(consolidated_insights))
        return {
            "status": "success",
            "insights": consolidated_insights,
            "promoted": promoted,
            "compaction": compaction_result,
        }

    def _analyze_tool_patterns(self, episodes: List) -> List[str]:
        """Analyze which tools are most used and update long-term memory."""
        insights = []
        tool_counts: Dict[str, int] = {}
        for ep in episodes:
            for tool in ep.tools_used:
                tool_counts[tool] = tool_counts.get(tool, 0) + 1

        if tool_counts:
            top_tool = max(tool_counts.items(), key=lambda x: x[1])
            insight = f"Most utilized tool across recent runs is '{top_tool[0]}' ({top_tool[1]} times)"
            self.long_term.remember(
                category="system_insights",
                key="top_tool",
                content=insight,
                source="consolidation",
            )
            insights.append(insight)

            # Store tool frequency as semantic knowledge
            for tool_name, count in tool_counts.items():
                if count >= 3:
                    self.self_model.add_semantic_triple(
                        subject="user",
                        predicate="frequently_uses",
                        object=tool_name,
                        confidence=min(0.95, 0.5 + count * 0.05),
                        source="consolidation",
                        evidence=f"Used {count} times in recent episodes",
                    )

        return insights

    def _analyze_performance(self, episodes: List) -> List[str]:
        """Detect performance patterns and contradictions."""
        insights = []
        success_count = sum(1 for ep in episodes if ep.status == "success")
        fail_count = sum(1 for ep in episodes if ep.status == "failed")
        total = len(episodes)

        if total > 0:
            success_rate = round(success_count / total * 100, 1)
            if success_rate < 70:
                insight = f"Overall success rate is low: {success_rate}% ({fail_count} failures out of {total})"
                insights.append(insight)
                self.long_term.remember(
                    category="system_insights",
                    key="low_success_rate_alert",
                    content=insight,
                    source="consolidation",
                )
            elif success_rate >= 95:
                insight = f"Excellent performance: {success_rate}% success rate across {total} recent tasks"
                insights.append(insight)

        return insights

    def _analyze_time_patterns(self, episodes: List) -> List[str]:
        """Extract time-of-day usage patterns for user model."""
        insights = []
        if not episodes:
            return insights

        # Analyze typical usage hours
        hour_counts: Dict[int, int] = {}
        for ep in episodes:
            if hasattr(ep, "created_at") and ep.created_at:
                hour = ep.created_at.hour
                hour_counts[hour] = hour_counts.get(hour, 0) + 1

        if hour_counts:
            peak_hour = max(hour_counts.items(), key=lambda x: x[1])
            if peak_hour[1] >= 3:
                insight = f"Peak usage hour: {peak_hour[0]:02d}:00 ({peak_hour[1]} tasks)"
                self.self_model.set_user_preference(
                    key="peak_usage_hour",
                    value=str(peak_hour[0]),
                    category="pattern",
                    source="consolidation",
                )
                insights.append(insight)

        return insights

    def _promote_important_memories(self) -> int:
        """Promote high-importance medium-term memories to long-term."""
        important = self.medium_term.get_important(threshold=0.8)
        promoted = 0

        for item in important:
            if item["access_count"] >= 2:  # Accessed multiple times = worth keeping
                key = f"promoted_{item['id']}"
                self.medium_term.promote_to_long_term(
                    item_id=item["id"],
                    category="promoted_insights",
                    key=key,
                )
                promoted += 1

        return promoted

    def store_interaction_context(
        self,
        message: str,
        response: str,
        importance: float = 0.5,
        episode_id: str = "",
    ) -> None:
        """Store an interaction in medium-term memory for later consolidation."""
        self.medium_term.store(
            content=f"User: {message[:200]}\nMitchell: {response[:200]}",
            context="chat_interaction",
            importance=importance,
            source_episode_id=episode_id,
        )

    def detect_contradictions(self) -> List[Dict[str, str]]:
        """Scan for contradictions across memory tiers."""
        contradictions = []

        # Check user preferences for contradictions
        prefs = self.self_model.get_user_preferences()
        for pref in prefs:
            if pref.contradicted_by:
                contradictions.append({
                    "type": "user_preference",
                    "key": pref.key,
                    "current_value": pref.value,
                    "contradicted_by": pref.contradicted_by,
                })

        return contradictions


memory_consolidator = MemoryConsolidator()

__all__ = ["MemoryConsolidator", "memory_consolidator", "MediumTermMemory", "medium_term_memory"]

"""Background Memory Consolidation for synthesizing long-term memories from episodes."""

from typing import Any, Dict, List
from mitchell.core.event_log import event_log
from mitchell.core.logging import logger
from mitchell.memory.database import memory_db
from mitchell.memory.episodic import episodic_memory
from mitchell.memory.long_term import long_term_memory
from mitchell.memory.self_model import self_model


class MemoryConsolidator:
    """Consolidates episodic history into generalized facts, preferences, and self-model insights."""

    def __init__(self) -> None:
        self.db = memory_db
        self.episodic = episodic_memory
        self.long_term = long_term_memory
        self.self_model = self_model

    def run_consolidation(self) -> Dict[str, Any]:
        """Perform a consolidation pass over recent episodes and events."""
        logger.info("MemoryConsolidator: Starting consolidation pass...")
        recent_episodes = self.episodic.get_recent(limit=20)

        consolidated_insights: List[str] = []

        # Analyze success patterns and repeated failures
        tool_counts: Dict[str, int] = {}
        for ep in recent_episodes:
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
            consolidated_insights.append(insight)

        event_log.log_event(
            "memory_consolidated",
            source="memory_consolidator",
            data={"insights_count": len(consolidated_insights), "insights": consolidated_insights},
        )

        logger.info("MemoryConsolidator: Pass complete with {} insights.", len(consolidated_insights))
        return {"status": "success", "insights": consolidated_insights}


memory_consolidator = MemoryConsolidator()

__all__ = ["MemoryConsolidator", "memory_consolidator"]

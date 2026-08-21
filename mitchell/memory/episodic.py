"""Episodic Memory tier for recording and searching historic job execution runs."""

import json
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from mitchell.core.event_log import event_log
from mitchell.core.logging import logger
from mitchell.memory.database import memory_db
from mitchell.memory.vector_store import vector_store


class Episode(BaseModel):
    """Structured record of a single task or job execution."""

    id: str = Field(default_factory=lambda: uuid.uuid4().hex[:12])
    goal: str = Field(..., description="Original goal or user prompt")
    status: str = Field(..., description="Outcome status: success | failed | aborted")
    plan: List[str] = Field(default_factory=list, description="Task graph or steps planned")
    steps: List[Dict[str, Any]] = Field(default_factory=list, description="Steps executed")
    tools_used: List[str] = Field(default_factory=list, description="List of tools invoked")
    outcome: str = Field(default="", description="Summary of final output or error")
    duration_s: float = Field(default=0.0, description="Total execution time in seconds")
    tokens_used: int = Field(default=0, description="Total tokens consumed")
    cost_inr: float = Field(default=0.0, description="Estimated cost in INR")
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class EpisodicMemory:
    """Manages persistent episodic run histories and RAG similarity retrieval."""

    def __init__(self) -> None:
        self.db = memory_db
        self.vector_store = vector_store

    def record(
        self,
        goal: str,
        status: str,
        plan: Optional[List[str]] = None,
        steps: Optional[List[Dict[str, Any]]] = None,
        tools_used: Optional[List[str]] = None,
        outcome: str = "",
        duration_s: float = 0.0,
        tokens_used: int = 0,
        cost_inr: float = 0.0,
    ) -> Episode:
        """Record a completed episode into persistent SQLite store and index for semantic search."""
        episode = Episode(
            goal=goal,
            status=status,
            plan=plan or [],
            steps=steps or [],
            tools_used=tools_used or [],
            outcome=outcome,
            duration_s=duration_s,
            tokens_used=tokens_used,
            cost_inr=cost_inr,
        )

        with self.db._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO episodic_memory (
                    id, goal, status, plan_json, steps_json, tools_used_json,
                    outcome, duration_s, tokens_used, cost_inr
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    episode.id,
                    episode.goal,
                    episode.status,
                    json.dumps(episode.plan),
                    json.dumps(episode.steps),
                    json.dumps(episode.tools_used),
                    episode.outcome,
                    episode.duration_s,
                    episode.tokens_used,
                    episode.cost_inr,
                ),
            )
            conn.commit()

        # Vector index for similarity matching on future similar goals
        index_text = f"Goal: {episode.goal} | Status: {episode.status} | Tools: {', '.join(episode.tools_used)} | Outcome: {episode.outcome}"
        self.vector_store.index("episode", episode.id, index_text)

        logger.info("Recorded Episode [{}] '{}' ({})", episode.id, episode.goal[:40], episode.status)
        event_log.log_event(
            "episode_recorded",
            source="episodic_memory",
            data={"episode_id": episode.id, "goal": episode.goal, "status": episode.status},
        )
        return episode

    def get_recent(self, limit: int = 10) -> List[Episode]:
        """Retrieve most recent episodes."""
        with self.db._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT id, goal, status, plan_json, steps_json, tools_used_json,
                       outcome, duration_s, tokens_used, cost_inr, created_at
                FROM episodic_memory
                ORDER BY created_at DESC LIMIT ?
                """,
                (limit,),
            )
            rows = cursor.fetchall()

        episodes: List[Episode] = []
        for row in rows:
            episodes.append(
                Episode(
                    id=row["id"],
                    goal=row["goal"],
                    status=row["status"],
                    plan=json.loads(row["plan_json"] or "[]"),
                    steps=json.loads(row["steps_json"] or "[]"),
                    tools_used=json.loads(row["tools_used_json"] or "[]"),
                    outcome=row["outcome"] or "",
                    duration_s=row["duration_s"] or 0.0,
                    tokens_used=row["tokens_used"] or 0,
                    cost_inr=row["cost_inr"] or 0.0,
                )
            )
        return episodes

    def search_similar(self, query: str, top_k: int = 4) -> List[Dict[str, Any]]:
        """Find past episodes similar to current goal."""
        return self.vector_store.search(query=query, entity_type="episode", top_k=top_k)


episodic_memory = EpisodicMemory()

__all__ = ["Episode", "EpisodicMemory", "episodic_memory"]

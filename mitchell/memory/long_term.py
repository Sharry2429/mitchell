"""Long-Term Memory tier for storing structured facts, preferences, and project context."""

import uuid
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from mitchell.core.event_log import event_log
from mitchell.core.logging import logger
from mitchell.memory.database import memory_db
from mitchell.memory.vector_store import vector_store


class LongTermEntry(BaseModel):
    """Structured long-term memory entry."""

    id: str = Field(default_factory=lambda: uuid.uuid4().hex[:12])
    category: str = Field(..., description="Category: preference | fact | project | config")
    key: str = Field(..., description="Unique key within category")
    content: str = Field(..., description="Memory text content")
    confidence: float = Field(default=1.0, description="Confidence score")
    source: str = Field(default="user", description="Origin: user | consolidation | agent")


class LongTermMemory:
    """Manages persistent semantic facts and user preferences."""

    def __init__(self) -> None:
        self.db = memory_db
        self.vector_store = vector_store

    def remember(
        self,
        category: str,
        key: str,
        content: str,
        confidence: float = 1.0,
        source: str = "user",
    ) -> LongTermEntry:
        """Store or update a factual or preference memory."""
        entry_id = f"{category}:{key}"
        entry = LongTermEntry(
            id=entry_id,
            category=category,
            key=key,
            content=content,
            confidence=confidence,
            source=source,
        )

        with self.db._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO long_term_memory (id, category, key, content, confidence, source, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                ON CONFLICT(category, key) DO UPDATE SET
                    content = excluded.content,
                    confidence = excluded.confidence,
                    source = excluded.source,
                    updated_at = CURRENT_TIMESTAMP
                """,
                (entry.id, entry.category, entry.key, entry.content, entry.confidence, entry.source),
            )
            conn.commit()

        # Index in vector store for semantic RAG search
        self.vector_store.index(
            entity_type="long_term_memory",
            entity_id=entry.id,
            text=f"[{category}] {key}: {content}",
        )

        logger.info("Remembered {}:{} -> '{}'", category, key, content[:50])
        event_log.log_event(
            "memory_remembered",
            source="long_term_memory",
            data={"category": category, "key": key, "content": content},
        )
        return entry

    def recall(self, category: str, key: str) -> Optional[str]:
        """Retrieve a specific memory by category and key."""
        with self.db._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT content FROM long_term_memory WHERE category = ? AND key = ?",
                (category, key),
            )
            row = cursor.fetchone()
            return row["content"] if row else None

    def recall_category(self, category: str) -> List[Dict[str, Any]]:
        """Retrieve all memories in a given category."""
        with self.db._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT id, category, key, content, confidence, source FROM long_term_memory WHERE category = ?",
                (category,),
            )
            rows = cursor.fetchall()
            return [dict(row) for row in rows]

    def search(self, query: str, top_k: int = 4) -> List[Dict[str, Any]]:
        """Semantic search across all long-term memories."""
        return self.vector_store.search(
            query=query,
            entity_type="long_term_memory",
            top_k=top_k,
        )

    def forget(self, category: str, key: str) -> bool:
        """Delete a memory item."""
        entry_id = f"{category}:{key}"
        with self.db._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "DELETE FROM long_term_memory WHERE category = ? AND key = ?",
                (category, key),
            )
            conn.commit()

        self.vector_store.delete("long_term_memory", entry_id)
        return True


long_term_memory = LongTermMemory()

__all__ = ["LongTermEntry", "LongTermMemory", "long_term_memory"]

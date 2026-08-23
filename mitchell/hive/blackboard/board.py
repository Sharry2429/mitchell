"""Shared Multi-Agent Blackboard for asynchronous coordination, artifacts, and claims."""

import time
import uuid
from typing import Any, Callable, Dict, List, Optional, Set
from pydantic import BaseModel, Field

from mitchell.core.event_log import event_log
from mitchell.core.logging import logger


class BlackboardEntry(BaseModel):
    """Single item posted on the shared Blackboard."""

    id: str = Field(default_factory=lambda: f"item_{uuid.uuid4().hex[:8]}")
    topic: str
    author: str
    content: Any
    timestamp: float = Field(default_factory=time.time)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class SharedBlackboard:
    """Thread-safe and async-safe collaborative whiteboard for Hive agents."""

    def __init__(self) -> None:
        self._topics: Dict[str, List[BlackboardEntry]] = {}
        self._claims: Dict[str, str] = {}  # task_id -> agent_id
        self._subscribers: Dict[str, Set[Callable[[BlackboardEntry], None]]] = {}

    def post(
        self,
        topic: str,
        content: Any,
        author: str = "agent",
        metadata: Optional[Dict[str, Any]] = None,
    ) -> BlackboardEntry:
        """Post a new artifact or finding to a blackboard topic."""
        entry = BlackboardEntry(
            topic=topic,
            author=author,
            content=content,
            metadata=metadata or {},
        )

        if topic not in self._topics:
            self._topics[topic] = []
        self._topics[topic].append(entry)

        logger.debug("Blackboard: [{}] posted by '{}'", topic, author)
        event_log.log_event(
            "blackboard_posted",
            source="blackboard",
            data={"topic": topic, "author": author, "entry_id": entry.id},
        )

        # Notify subscribers
        for callback in self._subscribers.get(topic, set()):
            try:
                callback(entry)
            except Exception as e:
                logger.error("Blackboard subscriber notification error: {}", e)

        return entry

    def read_topic(self, topic: str, limit: int = 10) -> List[BlackboardEntry]:
        """Read recent entries from a specific topic."""
        entries = self._topics.get(topic, [])
        return entries[-limit:]

    def list_topics(self) -> List[str]:
        """List all active blackboard topic names."""
        return list(self._topics.keys())

    def claim_task(self, task_id: str, agent_id: str) -> bool:
        """Claim a task on the blackboard for exclusive agent execution."""
        if task_id in self._claims:
            logger.warning("Task '{}' already claimed by '{}'", task_id, self._claims[task_id])
            return False

        self._claims[task_id] = agent_id
        logger.info("Blackboard: Task '{}' claimed by '{}'", task_id, agent_id)
        event_log.log_event(
            "blackboard_task_claimed",
            source="blackboard",
            data={"task_id": task_id, "agent_id": agent_id},
        )
        return True

    def release_task(self, task_id: str, agent_id: str) -> bool:
        """Release a previously claimed task."""
        if self._claims.get(task_id) == agent_id:
            del self._claims[task_id]
            logger.info("Blackboard: Task '{}' released by '{}'", task_id, agent_id)
            return True
        return False

    def subscribe(self, topic: str, callback: Callable[[BlackboardEntry], None]) -> None:
        """Subscribe to new entries on a topic."""
        if topic not in self._subscribers:
            self._subscribers[topic] = set()
        self._subscribers[topic].add(callback)

    def clear(self) -> None:
        """Reset the blackboard."""
        self._topics.clear()
        self._claims.clear()

    def dump_state(self) -> Dict[str, Any]:
        """Export full snapshot of active topics, entries, and claims."""
        return {
            "topics": {
                t: [e.model_dump(mode="json") for e in entries[-10:]]
                for t, entries in self._topics.items()
            },
            "claims": dict(self._claims),
            "total_topics": len(self._topics),
        }



blackboard = SharedBlackboard()

__all__ = ["BlackboardEntry", "SharedBlackboard", "blackboard"]

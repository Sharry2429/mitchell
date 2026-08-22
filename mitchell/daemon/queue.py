"""Persistent SQLite-backed task queue for Mitchell's autonomous daemon."""

import json
import sqlite3
import time
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional

from mitchell.core.config import settings
from mitchell.core.logging import logger


class DaemonTaskQueue:
    """Thread-safe persistent task queue with priorities and retry management."""

    def __init__(self, db_path: Optional[Path] = None) -> None:
        self.db_path = db_path or (settings.data_dir / "daemon_queue.db")
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self.db_path), timeout=15.0)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self) -> None:
        with self._get_connection() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS task_queue (
                    id TEXT PRIMARY KEY,
                    goal TEXT NOT NULL,
                    priority INTEGER DEFAULT 10,
                    status TEXT DEFAULT 'pending',
                    payload_json TEXT DEFAULT '{}',
                    retry_count INTEGER DEFAULT 0,
                    max_retries INTEGER DEFAULT 3,
                    created_at REAL NOT NULL,
                    updated_at REAL NOT NULL,
                    result_json TEXT
                )
            """)
            conn.commit()

    def enqueue(
        self,
        goal: str,
        priority: int = 10,
        payload: Optional[Dict[str, Any]] = None,
        max_retries: int = 3,
    ) -> str:
        """Enqueue a new autonomous goal into the persistent queue."""
        task_id = f"task_{uuid.uuid4().hex[:10]}"
        now = time.time()
        with self._get_connection() as conn:
            conn.execute(
                """
                INSERT INTO task_queue (id, goal, priority, status, payload_json, created_at, updated_at, max_retries)
                VALUES (?, ?, ?, 'pending', ?, ?, ?, ?)
                """,
                (task_id, goal, priority, json.dumps(payload or {}), now, now, max_retries),
            )
            conn.commit()
        logger.info("Daemon Queue: Enqueued task '{}' (priority={})", task_id, priority)
        return task_id

    def dequeue(self) -> Optional[Dict[str, Any]]:
        """Fetch the highest priority pending task and mark it as running."""
        with self._get_connection() as conn:
            row = conn.execute(
                """
                SELECT * FROM task_queue
                WHERE status = 'pending'
                ORDER BY priority DESC, created_at ASC
                LIMIT 1
                """
            ).fetchone()

            if not row:
                return None

            task_dict = dict(row)
            task_dict["payload"] = json.loads(task_dict.get("payload_json") or "{}")

            conn.execute(
                "UPDATE task_queue SET status = 'running', updated_at = ? WHERE id = ?",
                (time.time(), task_dict["id"]),
            )
            conn.commit()
            return task_dict

    def complete_task(self, task_id: str, result: Any, status: str = "completed") -> None:
        """Mark a task as completed or failed with result payload."""
        with self._get_connection() as conn:
            conn.execute(
                """
                UPDATE task_queue
                SET status = ?, result_json = ?, updated_at = ?
                WHERE id = ?
                """,
                (status, json.dumps(result, default=str), time.time(), task_id),
            )
            conn.commit()
        logger.info("Daemon Queue: Task '{}' marked as {}", task_id, status)

    def count_pending(self) -> int:
        """Get count of pending tasks."""
        with self._get_connection() as conn:
            cur = conn.execute("SELECT COUNT(*) FROM task_queue WHERE status = 'pending'")
            return cur.fetchone()[0]


daemon_queue = DaemonTaskQueue()

__all__ = ["DaemonTaskQueue", "daemon_queue"]

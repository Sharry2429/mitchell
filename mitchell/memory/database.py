"""SQLite database manager for Mitchell Memory and Vector storage."""

import json
import sqlite3
from pathlib import Path
from typing import Any, Dict, List, Optional

from mitchell.core.config import settings
from mitchell.core.logging import logger


class MemoryDB:
    """Thread-safe SQLite database manager for long-term memory, episodic logs, and embeddings."""

    def __init__(self, db_path: Optional[Path] = None) -> None:
        self.db_path = Path(db_path or (Path(settings.data_dir) / "memory.sqlite3"))
        self._ensure_tables()

    def _get_connection(self) -> sqlite3.Connection:
        """Create a new connection with row factory."""
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(str(self.db_path), timeout=10)
        conn.row_factory = sqlite3.Row
        return conn

    def _ensure_tables(self) -> None:
        """Initialize database schema."""
        with self._get_connection() as conn:
            cursor = conn.cursor()

            # 1. Long-Term Memory (facts, preferences, project context)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS long_term_memory (
                    id TEXT PRIMARY KEY,
                    category TEXT NOT NULL,
                    key TEXT NOT NULL,
                    content TEXT NOT NULL,
                    confidence REAL DEFAULT 1.0,
                    source TEXT DEFAULT 'user',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(category, key)
                )
            """)

            # 2. Episodic Memory (complete job run records)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS episodic_memory (
                    id TEXT PRIMARY KEY,
                    goal TEXT NOT NULL,
                    status TEXT NOT NULL,
                    plan_json TEXT,
                    steps_json TEXT,
                    tools_used_json TEXT,
                    outcome TEXT,
                    duration_s REAL DEFAULT 0.0,
                    tokens_used INTEGER DEFAULT 0,
                    cost_inr REAL DEFAULT 0.0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # 3. Vector Embeddings (for RAG semantic retrieval)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS vector_store (
                    id TEXT PRIMARY KEY,
                    entity_type TEXT NOT NULL,
                    entity_id TEXT NOT NULL,
                    text_content TEXT NOT NULL,
                    embedding_json TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # 4. Self-Model & Capability Stats
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS self_model (
                    capability_name TEXT PRIMARY KEY,
                    category TEXT NOT NULL,
                    total_runs INTEGER DEFAULT 0,
                    successes INTEGER DEFAULT 0,
                    failures INTEGER DEFAULT 0,
                    avg_duration_s REAL DEFAULT 0.0,
                    avg_tokens INTEGER DEFAULT 0,
                    confidence REAL DEFAULT 0.5,
                    known_gaps TEXT,
                    preferred_strategy TEXT,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # 5. Skill Store (persisted skills)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS skills (
                    id TEXT PRIMARY KEY,
                    name TEXT UNIQUE NOT NULL,
                    version TEXT NOT NULL,
                    description TEXT NOT NULL,
                    tags_json TEXT,
                    source TEXT DEFAULT 'organic',
                    skill_json TEXT NOT NULL,
                    confidence REAL DEFAULT 0.8,
                    executions INTEGER DEFAULT 0,
                    successes INTEGER DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            conn.commit()


memory_db = MemoryDB()

__all__ = ["MemoryDB", "memory_db"]

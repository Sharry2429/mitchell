"""Health Watchdog daemon monitoring worker heartbeats, database access, and locks."""

import time
from typing import Any, Dict, List
from mitchell.core.event_log import event_log
from mitchell.core.lock import lock_manager
from mitchell.core.logging import logger
from mitchell.hive.router import hive_router
from mitchell.memory.database import memory_db


class SystemWatchdog:
    """Monitors system health, Hive agent connectivity, and active resource locks."""

    def __init__(self) -> None:
        self.lock_mgr = lock_manager
        self.hive = hive_router
        self.db = memory_db

    def run_health_check(self) -> Dict[str, Any]:
        """Perform comprehensive health inspection across all pillars and services."""
        logger.debug("SystemWatchdog: Running health check pass...")

        # 1. Database check
        db_healthy = False
        try:
            with self.db._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT 1")
                db_healthy = True
        except Exception as e:
            logger.error("SystemWatchdog: Database check failed: {}", e)

        # 2. Hive Agent registration check
        agents = self.hive.list_agents()
        active_agent_ids = [a["agent_id"] for a in agents]

        # 3. Active Locks check
        active_locks = self.lock_mgr.list_active_locks()

        status = "healthy" if db_healthy and len(active_agent_ids) >= 4 else "degraded"

        report = {
            "status": status,
            "database_connected": db_healthy,
            "registered_agents_count": len(active_agent_ids),
            "agents": active_agent_ids,
            "active_locks": active_locks,
            "timestamp": time.time(),
        }

        event_log.log_event(
            "health_heartbeat",
            source="watchdog",
            data={"status": status, "agents_count": len(active_agent_ids), "locks_count": len(active_locks)},
        )

        return report


watchdog = SystemWatchdog()

__all__ = ["SystemWatchdog", "watchdog"]

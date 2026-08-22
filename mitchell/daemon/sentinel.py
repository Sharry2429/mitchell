"""Health watchdog and process sentinel for Mitchell's autonomous daemon."""

import os
import subprocess
import sys
import time
from typing import Any, Dict, List

from mitchell.core.event_log import event_log
from mitchell.core.logging import logger


class DaemonSentinel:
    """Monitors system resource utilization, memory health, and orphaned processes."""

    def __init__(self) -> None:
        self.last_check_ts: float = 0.0

    def check_system_health(self) -> Dict[str, Any]:
        """Inspect platform status, disk space, and process responsiveness."""
        self.last_check_ts = time.time()
        health = {
            "timestamp": self.last_check_ts,
            "status": "healthy",
            "platform": sys.platform,
            "python_version": sys.version.split()[0],
            "warnings": [],
        }

        # Check disk space if os.statvfs available
        try:
            if hasattr(os, "statvfs"):
                st = os.statvfs(".")
                free_mb = (st.f_bavail * st.f_frsize) / (1024 * 1024)
                health["free_disk_mb"] = free_mb
                if free_mb < 500:
                    health["warnings"].append("Low disk space (<500MB)")
                    health["status"] = "degraded"
        except Exception as e:
            logger.debug("Disk check exception: {}", e)

        return health

    def cleanup_orphaned_processes(self) -> Dict[str, Any]:
        """Gracefully terminate any orphaned zombie browser or helper processes."""
        cleaned = 0
        # Placeholder for platform-specific cleanup if needed
        event_log.log_event(
            "sentinel_cleanup",
            source="daemon_sentinel",
            data={"cleaned_processes": cleaned},
        )
        return {"status": "ok", "cleaned": cleaned}


daemon_sentinel = DaemonSentinel()

__all__ = ["DaemonSentinel", "daemon_sentinel"]

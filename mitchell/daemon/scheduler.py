"""Recurring 5-field cron job scheduler for Mitchell's autonomous daemon."""

import datetime
import re
import time
from typing import Any, Callable, Dict, List, Optional

from mitchell.core.logging import logger
from mitchell.daemon.queue import daemon_queue


class CronJob:
    """Represents a scheduled routine with a cron expression."""

    def __init__(self, job_id: str, cron_expr: str, goal: str, priority: int = 10) -> None:
        self.job_id = job_id
        self.cron_expr = cron_expr.strip()
        self.goal = goal
        self.priority = priority
        self.last_run_ts: float = 0.0

    def matches_time(self, dt: datetime.datetime) -> bool:
        """Evaluate if the 5-field cron expression matches the given datetime."""
        parts = self.cron_expr.split()
        if len(parts) != 5:
            # Fallback to true if invalid expression
            return False

        minute, hour, dom, month, dow = parts

        def match_field(val: int, expr: str) -> bool:
            if expr == "*":
                return True
            if expr.startswith("*/"):
                try:
                    step = int(expr[2:])
                    return (val % step) == 0
                except ValueError:
                    return False
            if "," in expr:
                return str(val) in expr.split(",")
            try:
                return val == int(expr)
            except ValueError:
                return False

        # dow: 0=Monday in python datetime vs standard 0=Sunday or 0=Monday; handle 0-6
        return (
            match_field(dt.minute, minute)
            and match_field(dt.hour, hour)
            and match_field(dt.day, dom)
            and match_field(dt.month, month)
            and match_field(dt.weekday(), dow)
        )


class CronScheduler:
    """Manages and triggers recurring cron routines."""

    def __init__(self) -> None:
        self.jobs: Dict[str, CronJob] = {}

    def add_job(self, job_id: str, cron_expr: str, goal: str, priority: int = 10) -> CronJob:
        """Register a new recurring task."""
        job = CronJob(job_id=job_id, cron_expr=cron_expr, goal=goal, priority=priority)
        self.jobs[job_id] = job
        logger.info("CronScheduler: Registered job '{}' -> '{}' ({})", job_id, goal, cron_expr)
        return job

    def remove_job(self, job_id: str) -> bool:
        """Remove a registered cron job."""
        if job_id in self.jobs:
            del self.jobs[job_id]
            logger.info("CronScheduler: Removed job '{}'", job_id)
            return True
        return False

    def list_jobs(self) -> List[Dict[str, Any]]:
        """List all active recurring jobs."""
        return [
            {
                "job_id": j.job_id,
                "cron_expr": j.cron_expr,
                "goal": j.goal,
                "priority": j.priority,
                "last_run_ts": j.last_run_ts,
            }
            for j in self.jobs.values()
        ]

    def tick(self, now_dt: Optional[datetime.datetime] = None) -> List[str]:
        """Check all jobs and enqueue matching tasks if not already run in the current minute."""
        now = now_dt or datetime.datetime.now()
        current_minute_key = now.strftime("%Y-%m-%d %H:%M")
        triggered = []

        for job in self.jobs.values():
            if job.matches_time(now):
                # Ensure we run at most once per minute
                last_dt = datetime.datetime.fromtimestamp(job.last_run_ts) if job.last_run_ts else None
                if last_dt and last_dt.strftime("%Y-%m-%d %H:%M") == current_minute_key:
                    continue

                job.last_run_ts = time.time()
                daemon_queue.enqueue(goal=job.goal, priority=job.priority, payload={"cron_job_id": job.job_id})
                triggered.append(job.job_id)
                logger.info("CronScheduler: Triggered cron job '{}'", job.job_id)

        return triggered


cron_scheduler = CronScheduler()

__all__ = ["CronJob", "CronScheduler", "cron_scheduler"]

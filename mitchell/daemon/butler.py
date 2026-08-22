"""Continuous 24/7 background butler for Mitchell."""

import time
from typing import Optional

from mitchell.core.event_log import event_log
from mitchell.core.logging import logger
from mitchell.daemon.queue import daemon_queue
from mitchell.daemon.scheduler import cron_scheduler
from mitchell.daemon.sentinel import daemon_sentinel
from mitchell.manager import Manager


class MitchellButler:
    """Always-on queue-draining worker and proactive routine coordinator."""

    def __init__(self, manager_instance: Optional[Manager] = None) -> None:
        self.is_running = False
        self.queue = daemon_queue
        self.scheduler = cron_scheduler
        self.sentinel = daemon_sentinel
        self._manager = manager_instance

    @property
    def manager(self) -> Manager:
        if self._manager is None:
            self._manager = Manager()
        return self._manager

    def run_single_step(self) -> bool:
        """Perform one iteration of cron checking and queue task draining. Returns True if work was done."""
        # 1. Tick Cron Scheduler
        self.scheduler.tick()

        # 2. Dequeue pending task
        task = self.queue.dequeue()
        if not task:
            return False

        task_id = task["id"]
        goal = task["goal"]
        logger.info("Butler: Executing goal for task '{}': '{}'", task_id, goal)

        try:
            result = self.manager.run(goal)
            self.queue.complete_task(task_id=task_id, result=result, status="completed")
            event_log.log_event(
                "butler_task_success",
                source="butler",
                data={"task_id": task_id, "goal": goal},
            )
        except Exception as e:
            logger.error("Butler: Error executing task '{}': {}", task_id, e)
            self.queue.complete_task(task_id=task_id, result={"error": str(e)}, status="failed")
            event_log.log_event(
                "butler_task_failed",
                source="butler",
                data={"task_id": task_id, "error": str(e)},
            )

        return True

    def start_loop(self, poll_interval_s: float = 1.0) -> None:
        """Run the persistent Butler loop until interrupted."""
        self.is_running = True
        logger.info("Mitchell Butler: 24/7 background loop started.")
        event_log.log_event("butler_started", source="butler")

        try:
            while self.is_running:
                worked = self.run_single_step()
                if not worked:
                    time.sleep(poll_interval_s)
        except KeyboardInterrupt:
            logger.info("Mitchell Butler: Received shutdown signal.")
        finally:
            self.is_running = False
            event_log.log_event("butler_stopped", source="butler")
            logger.info("Mitchell Butler: Stopped.")

    def stop(self) -> None:
        """Stop the butler loop."""
        self.is_running = False


butler = MitchellButler()

__all__ = ["MitchellButler", "butler"]

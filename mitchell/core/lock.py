"""Global Resource Lock Manager preventing multi-agent collisions on devices, windows, and browser profiles."""

import asyncio
import time
from typing import Dict, Optional, Set
from pydantic import BaseModel, Field

from mitchell.core.event_log import event_log
from mitchell.core.logging import logger


class ResourceLock(BaseModel):
    """Resource lock entry with lease duration."""

    resource_id: str
    owner_agent: str
    acquired_at: float = Field(default_factory=time.time)
    lease_seconds: float = 30.0

    @property
    def is_expired(self) -> bool:
        """Check if lock has timed out."""
        return (time.time() - self.acquired_at) > self.lease_seconds


class ResourceLockManager:
    """Coordinates mutually exclusive access to physical and virtual resources."""

    def __init__(self) -> None:
        self._locks: Dict[str, ResourceLock] = {}
        self._async_locks: Dict[str, asyncio.Lock] = {}

    def acquire(
        self,
        resource_id: str,
        owner_agent: str,
        lease_seconds: float = 30.0,
        timeout: float = 5.0,
    ) -> bool:
        """Synchronously attempt to acquire a lock on resource_id."""
        start = time.time()
        while time.time() - start < timeout:
            current_lock = self._locks.get(resource_id)
            if current_lock is None or current_lock.is_expired:
                self._locks[resource_id] = ResourceLock(
                    resource_id=resource_id,
                    owner_agent=owner_agent,
                    lease_seconds=lease_seconds,
                )
                logger.debug("Resource lock '{}' acquired by '{}'", resource_id, owner_agent)
                event_log.log_event(
                    "resource_lock_acquired",
                    source="lock_manager",
                    data={"resource_id": resource_id, "owner": owner_agent},
                )
                return True
            if current_lock.owner_agent == owner_agent:
                # Re-entrant / renewal
                current_lock.acquired_at = time.time()
                current_lock.lease_seconds = lease_seconds
                return True
            time.sleep(0.1)

        logger.warning("Resource lock '{}' timed out for agent '{}'", resource_id, owner_agent)
        return False

    def release(self, resource_id: str, owner_agent: str) -> bool:
        """Release a previously acquired lock."""
        current_lock = self._locks.get(resource_id)
        if current_lock and current_lock.owner_agent == owner_agent:
            del self._locks[resource_id]
            logger.debug("Resource lock '{}' released by '{}'", resource_id, owner_agent)
            event_log.log_event(
                "resource_lock_released",
                source="lock_manager",
                data={"resource_id": resource_id, "owner": owner_agent},
            )
            return True
        return False

    def is_locked(self, resource_id: str) -> bool:
        """Check if resource is currently actively locked."""
        lock = self._locks.get(resource_id)
        if lock and not lock.is_expired:
            return True
        return False

    def list_active_locks(self) -> Dict[str, str]:
        """Return dict of currently held active locks."""
        return {
            res_id: lock.owner_agent
            for res_id, lock in self._locks.items()
            if not lock.is_expired
        }


lock_manager = ResourceLockManager()

__all__ = ["ResourceLock", "ResourceLockManager", "lock_manager"]

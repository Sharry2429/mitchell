"""
mitchell.core.warm_pool
=======================
Pre-spawns and maintains idle instances of team roles to eliminate cold starts.
"""

import asyncio

_idle_workers = {
    "windows_worker": [],
    "android_worker": [],
    "browser_worker": [],
    "researcher": []
}

async def pre_warm_pool():
    """Start up one idle instance for each role."""
    for role in _idle_workers.keys():
        _start_idle_worker(role)

def _start_idle_worker(role: str):
    """Spin up a background process/task for the role."""
    # In v1, this is mocked as adding a readiness flag.
    # A full implementation would spawn a subprocess with the role prompt
    # listening to its inbox on the hive.
    _idle_workers[role].append({"status": "idle", "role": "role"})

def claim_worker(role: str) -> dict | None:
    """Claim a warm worker, triggering a background replacement."""
    if role not in _idle_workers:
        return None
        
    pool = _idle_workers[role]
    if not pool:
        # Fallback to cold start if pool empty
        _start_idle_worker(role)
        return {"status": "cold_start", "role": role}
        
    worker = pool.pop(0)
    # Replenish in background
    asyncio.create_task(_replenish_worker(role))
    return worker

async def _replenish_worker(role: str):
    """Background task to replace a claimed worker."""
    await asyncio.sleep(0.1) # Simulate spawn time
    _start_idle_worker(role)

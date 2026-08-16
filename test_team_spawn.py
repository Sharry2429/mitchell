import asyncio
import time
from mitchell.core.warm_pool import pre_warm_pool, _idle_workers
from mitchell.agents.team import team_spawn, team_status

async def main():
    print("Testing team_spawn latency...")
    await pre_warm_pool()
    
    start = time.time()
    agent_id = team_spawn("windows_worker", "check volume")
    elapsed = time.time() - start
    
    print(f"Spawn took {elapsed:.4f}s")
    assert elapsed < 1.0, f"Spawn took too long: {elapsed}s"
    
    status = team_status(agent_id)
    assert status["status"] == "starting"
    print("Team spawn latency verified under 1 second.")
    
    # Check that warm_pool is now empty for windows_worker temporarily
    assert len(_idle_workers["windows_worker"]) == 0
    print("Worker failure report (simulated): worker claimed correctly.")

if __name__ == "__main__":
    asyncio.run(main())

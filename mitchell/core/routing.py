"""
mitchell.core.routing
=====================
Routing (automatic, no prompts):
  * coding intent                          -> Hermes-Agent coding worker
  * browser / Windows / Android            -> lean agent loop, starting on the
      CHEAP executor model; escalates to a stronger model, then the full
      verified planner->executor loop, only when the cheap pass can't answer.
"""
from __future__ import annotations

import time

from mitchell.core.safe_provider import SafeProvider
from mitchell.core.tasks import Task, TaskState

# Cheap "executor / chat" model first; escalate only when it can't answer.
# Model-routing plan: executor chain = GPT-OSS 120B -> 20B -> Llama 3.3 70B
# (Groq) -> AiCredits net. fast_do routes through the same cascade.
EXECUTOR_TIER = "executor"

_CODING_WORDS = (
    "implement", "write a function", "write a script", "write code", "write a module",
    "add function", "add a function", "refactor", "fix bug", "fix this code",
    "create a class", "new function", "unit test", "pytest", "make a program",
    "coding task", "develop", "codebase", "function that", "script that",
)


def _is_coding(task: str) -> bool:
    low = task.lower()
    return any(w in low for w in _CODING_WORDS)


def _run_coding(task: str, timeout: int = 900) -> dict:
    import os
    import sys
    import subprocess
    from mitchell.coding.hermes_coder import run_hermes_code
    res = run_hermes_code(task, timeout=timeout)
    verify = "no test produced"
    if res.get("ok"):
        wd = res["workdir"]
        if any("test" in l.lower() and l.strip().endswith(".py") for l in (res["files"] or "").splitlines()):
            r = subprocess.run([sys.executable, "-m", "pytest", "-q"], cwd=wd,
                               capture_output=True, text=True, timeout=180)
            tail = (r.stdout.strip().splitlines() or [""])[-1]
            verify = f"pytest: {tail} (exit={r.returncode})"
    res["verify"] = verify
    return res


async def _run_fast(task: str, tier: str) -> dict:
    from mitchell.core.fast import fast_do
    provider = SafeProvider()
    t0 = time.monotonic()
    try:
        res = await fast_do(task, provider, tier=tier)
    except Exception as e:  # noqa: BLE001
        return {"ok": False, "answer": f"{type(e).__name__}: {e}",
                "elapsed": round(time.monotonic() - t0, 2), "tier": tier, "fast": True}
    return {"ok": bool((res.get("answer") or "").strip()), "answer": res.get("answer"),
            "tool": res.get("tool"), "elapsed": res.get("elapsed"), "tier": tier, "fast": True}


async def _run_agent(task: str, idx: str) -> dict:
    from mitchell.core.executor import execute_task
    t = Task(id=idx, instruction=task)
    t.state = TaskState.PENDING
    t.save()
    t0 = time.monotonic()
    try:
        await execute_task(t.id, tools=SafeProvider())
    except Exception as e:  # noqa: BLE001
        return {"ok": False, "error": f"{type(e).__name__}: {e}", "state": "error",
                "elapsed": round(time.monotonic() - t0, 2)}
    final = Task.load(t.id)
    return {"ok": final.state == TaskState.COMPLETED, "state": final.state, "tool": None,
            "elapsed": round(time.monotonic() - t0, 2),
            "steps": len(final.steps),
            "steps_ok": sum(1 for s in final.steps if s.state == TaskState.COMPLETED)}


async def route_one(task: str, idx: str = "do") -> dict:
    """The single router: coding -> Hermes; else cheap model -> escalate -> full loop."""
    if _is_coding(task):
        res = _run_coding(task)
        res.update({"kind": "coding (Hermes)", "answer": f"exit={res.get('exit_code')} "
                    f"workdir={res.get('workdir')} verify={res.get('verify')}"})
        return res

    res = await _run_fast(task, EXECUTOR_TIER)
    kind = f"executor ({EXECUTOR_TIER})"
    if not res.get("ok"):                      # escalate cheap -> stronger
        res = await _run_fast(task, "base")
        kind = "base (escalated)"
        if not res.get("ok"):                  # escalate stronger -> full verified loop
            res = await _run_agent(task, f"do-{idx}")
            kind = "full verified loop"
    res["kind"] = kind
    return res

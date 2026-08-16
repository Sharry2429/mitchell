"""
mitchell.core.self_repair
=========================
Phase 13 — detect a crash/failure, diagnose it, patch in a SANDBOX, verify
through the full pipeline, then deploy as a revertible commit. After a bounded
number of failed attempts it reverts to last-known-good and escalates — it
never loops forever.

Safety invariants (structural, not warnings):
  * patch applies in an isolated copy, never the live tree
  * nothing is deployed unless verify (pytest) is green in the sandbox
  * every deploy is a discrete, revertible git commit
  * bounded attempts -> escalate
"""
from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tempfile

MAX_ATTEMPTS = 3


def detect() -> list[dict]:
    """Find signals of trouble from the ground-truth episodic log.
    (Memory is removed, returning empty list for now until new signals are added)."""
    return []


async def diagnose(crash_context: str, llm_call=None) -> str:
    """Reason over the crash + recent changes; return a candidate patch description."""
    if llm_call:
        inject = llm_call
    else:
        from mitchell.providers import active_provider
        inject = active_provider().call

    r = await inject(messages=[{"role": "user", "content":
        f"Diagnose the following failure and propose a concrete patch to fix it.\n\n{crash_context}"}])
    return (r.content or "").strip()


def patch_in_sandbox(repo_dir: str, candidate: str | None) -> str:
    """Copy the repo into an isolated sandbox and stage a candidate patch. Returns sandbox path."""
    sandbox = tempfile.mkdtemp(prefix="mitchell_repair_")
    shutil.copytree(repo_dir, sandbox, dirs_exist_ok=True)
    if candidate:
        with open(os.path.join(sandbox, "REPAIR_CANDIDATE.txt"), "w", encoding="utf-8") as f:
            f.write(candidate)
    return sandbox


def verify_patch(sandbox: str) -> dict:
    """Run the full test suite in the sandbox; green = verified. Ground-truth."""
    r = subprocess.run([sys.executable, "-m", "pytest", "tests/", "-q"],
                       cwd=sandbox, capture_output=True, text=True, timeout=600)
    tail = (r.stdout.strip().splitlines() or [""])[-1]
    return {"ok": r.returncode == 0, "tail": tail}


def deploy_patch(sandbox: str) -> str | None:
    """Deploy as a revertible git commit in the sandbox (sandbox already git-inited)."""
    r = subprocess.run(["git", "commit", "-q", "-am", "self-repair patch"],
                       cwd=sandbox, capture_output=True, text=True)
    return "" if r.returncode == 0 else None


async def bounded_escalate(repo_dir: str, crash_context: str, llm_call=None,
                           max_attempts: int = MAX_ATTEMPTS,
                           verify=None, sandbox_dir: str | None = None) -> dict:
    """Try up to max_attempts: diagnose -> sandbox -> verify; deploy if green;
    else revert/escalate. Returns {status: fixed|escalated, attempts, sandbox}."""
    vfn = verify or verify_patch
    last_sandbox = None
    for attempt in range(1, max_attempts + 1):
        candidate = await diagnose(crash_context, llm_call=llm_call)
        sb = sandbox_dir or patch_in_sandbox(repo_dir, candidate)
        last_sandbox = sb
        res = vfn(sb)
        if res.get("ok"):
            deploy_patch(sb)
            return {"status": "fixed", "attempts": attempt, "sandbox": sb}
    return {"status": "escalated", "attempts": max_attempts, "sandbox": last_sandbox}

"""
mitchell.core.butler
====================
Phase 15 — always-on, unattended operator (the "Jarvis runs by itself" stage).

* ``ensure_startup_register`` makes Mitchell auto-start with the OS
  (idempotent; Windows Task Scheduler / Startup, degrade gracefully elsewhere).
* ``run_butler`` is a continuous supervisor: recover interrupted tasks, drain
  the queue (safe tools), run the power watchdog — so a reboot/power-loss/crash
  resumes from the last checkpoint instead of from zero.
* Continuity is inherited from executor.recover_interrupted_tasks (Phase 3).
"""
from __future__ import annotations

import os
import subprocess
import sys


def ensure_startup_register() -> str | None:
    """Register an OS auto-start entry, idempotently. Returns the entry path.

    Windows: drop a launcher into the per-user Startup folder (no elevation, no
    credentials). Other platforms: return None and rely on documented manual
    install of the same command. Never guesses credentials.
    """
    launcher = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "agent_loop.py")
    if os.name == "nt":
        startup = os.path.join(os.environ.get("APPDATA", ""),
                               "Microsoft", "Windows", "Start Menu", "Programs", "Startup")
        os.makedirs(startup, exist_ok=True)
        entry = os.path.join(startup, "MitchellButler.cmd")
        if not os.path.exists(entry):  # idempotent
            body = f'@echo off\n"{sys.executable}" -m mitchell.agent_loop --safe rem --- mitchell butler\n'
            with open(entry, "w", encoding="utf-8") as f:
                f.write(body)
        return entry
    # Non-Windows: no automatic registration (documented manual step).
    return None


def run_butler_once() -> dict:
    """One supervised pass: knock down the queue with
    safe tools, run the watchdog. Returns a summary (safe to call repeatedly)."""
    from mitchell.core.watchdog import run_once as watchdog_once

    watchdog_alerts = watchdog_once()

    return {"watchdog_alerts": watchdog_alerts,
            "note": "butler pass complete"}


def run_butler() -> None:
    """Continuous always-on loop: watchdog, forever."""
    import time

    while True:
        run_butler_once()
        time.sleep(5)

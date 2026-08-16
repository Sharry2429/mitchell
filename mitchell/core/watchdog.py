"""
mitchell.core.watchdog
======================
Battery / power health watchdog (Phase 10).

Polls laptop (psutil) and Android phone (adb battery via subprocess) levels.
When a threshold is crossed it emits a proactive alert BEFORE an outage, and
logs it to the episodic store so it's part of the ground-truth record.
Runs detached from the task loop so it can run continuously (see butler).
"""
from __future__ import annotations

import subprocess
import time

LAPTOP_LOW = 50      # % below which we nag to plug the laptop in
PHONE_LOW = 20       # % below which we nag to plug the phone in


def laptop_battery() -> dict:
    """Return {has_battery, percent, charging}; has_battery=False on desktops."""
    try:
        import psutil
        b = psutil.sensors_battery()
        if b is None:
            return {"has_battery": False}
        return {"has_battery": True, "percent": b.percent, "charging": bool(b.power_plugged)}
    except Exception:  # noqa: BLE001
        return {"has_battery": False}


def phone_battery() -> int | None:
    """Return phone battery % via adb, or None if no device / unavailable."""
    try:
        out = subprocess.run(["adb", "shell", "dumpsys", "battery"],
                             capture_output=True, text=True, timeout=10)
        for line in out.stdout.splitlines():
            if line.strip().startswith("level:"):
                return int(line.split(":", 1)[1].strip())
    except Exception:  # noqa: BLE001
        pass
    return None


def check_thresholds(laptop_lt: int = LAPTOP_LOW, phone_lt: int = PHONE_LOW) -> list[str]:
    """Produce a list of alert strings for any crossed threshold."""
    alerts: list[str] = []
    lap = laptop_battery()
    if lap.get("has_battery") and lap["percent"] < laptop_lt:
        stage = "charging" if lap["charging"] else "on battery"
        alerts.append(f"[POWER] Laptop at {lap['percent']}% ({stage}) < {laptop_lt}%. Plug in soon.")
    ph = phone_battery()
    if ph is not None and ph < phone_lt:
        alerts.append(f"[POWER] Phone at {ph}% < {phone_lt}%. Plug in soon.")
        
    try:
        from mitchell.core.warm_pool import _idle_workers
        for role, pool in _idle_workers.items():
            if not pool:
                alerts.append(f"[POOL] Worker pool empty for role: {role}")
    except Exception:
        pass
        
    return alerts

def proactive_alert(message: str) -> str:
    """Emit an alert (logging it locally)."""
    try:
        print(message)
    except Exception:
        pass
    return message


def run_once() -> list[str]:
    """Check thresholds once, emit an alert per crossed one. Returns alerts."""
    alerts = check_thresholds()
    for a in alerts:
        proactive_alert(a)
    return alerts


def run_loop(interval: float = 300.0) -> None:
    """Run forever, checking + alerting on a fixed interval."""
    while True:
        run_once()
        time.sleep(interval)

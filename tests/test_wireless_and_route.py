"""
Single-interface routing (do.route_one): cheap executor model first, escalate on
demand; and the wireless-adb (USB-once -> Tailscale) setup. Deterministic, mocked.
"""
import asyncio

import mitchell.core.routing as do
import mitchell.android.wireless as wl


def _run(coro):
    return asyncio.run(coro)


# ---------------- routing / escalation (single interface) ----------------#

def test_route_coding_goes_to_hermes(monkeypatch):
    monkeypatch.setattr(do, "_run_coding", lambda task, timeout=900: {"ok": True, "workdir": "/w", "verify": "pytest: 1 passed"})
    res = _run(do.route_one("implement a function double(x)"))
    assert res["kind"].startswith("coding")


def test_route_fast_ok_uses_executor_model(monkeypatch):
    async def fast(task, tier):
        return {"ok": True, "answer": "Title: Example Domain", "tier": tier, "elapsed": 1}
    monkeypatch.setattr(do, "_run_fast", fast)
    res = _run(do.route_one("open example.com and report the title"))
    assert res["ok"] and res["kind"] == f"executor ({do.EXECUTOR_TIER})"


def test_route_escalates_cheap_stronger_then_full_loop(monkeypatch):
    order = []

    async def fast(task, tier):
        order.append(("fast", tier))
        return {"ok": False, "answer": "", "tier": tier, "elapsed": 1}

    async def agent(task, idx):
        order.append(("agent",))
        return {"ok": True, "answer": "full", "elapsed": 2, "state": "completed"}

    monkeypatch.setattr(do, "_run_fast", fast)
    monkeypatch.setattr(do, "_run_agent", agent)
    res = _run(do.route_one("open example.com"))
    assert order == [("fast", do.EXECUTOR_TIER), ("fast", "base"), ("agent",)]
    assert res["kind"] == "full verified loop"


# ---------------- wireless adb over tailscale ----------------#

def test_wireless_setup_ok(monkeypatch):
    def fake_adb(*args):
        if args[0] == "devices":
            return "List of devices attached\n70e3a981\tdevice\n"
        if args[0] == "connect":
            return "connected to 100.1.2.3:5555"
        if "getprop" in args:
            return "CPH2707\n"
        return ""
    monkeypatch.setattr(wl, "_adb", fake_adb)
    monkeypatch.setattr(wl, "_find_usb_serial", lambda: "70e3a981")
    monkeypatch.setattr(wl, "_tailscale_android_ip", lambda: "100.1.2.3")
    res = wl.setup()
    assert res["ok"] is True
    assert res["target"] == "100.1.2.3:5555"
    assert res["model"] == "CPH2707"
    assert "unplug" in res["next"].lower()


def test_wireless_setup_requires_usb_once(monkeypatch):
    monkeypatch.setattr(wl, "_find_usb_serial", lambda: None)
    res = wl.setup()
    assert res["ok"] is False and "USB" in res["error"]


def test_tailscale_ip_detection(monkeypatch):
    import subprocess as sp
    class R:
        stdout = "100.91.251.126 sharryog windows\n100.81.132.46 oneplus-nord-5 android\n"
    monkeypatch.setattr(wl.subprocess, "run", lambda *a, **k: R())
    assert wl._tailscale_android_ip() == "100.81.132.46"

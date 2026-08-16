"""
mitchell.android.wireless
=========================
Wireless adb over Tailscale, the "plug USB once, then go wireless" flow:

    1. (user) plug the phone into the PC over USB once, enable USB debugging
    2. setup()  -> tells the phone to listen on tcp:5555, then adb-connects to
                   the Tailscale (or WiFi) IP
    3. (user) unplug USB; Mitchell keeps talking to the phone over the network

Requires: `adb` on PATH; the phone authorized (it already is once it shows as
`device` over USB). No credentials are guessed.
"""
from __future__ import annotations

import os
import re
import subprocess

DEFAULT_PORT = 5555


def _adb(*args: str) -> str:
    return subprocess.run(["adb", *args], capture_output=True, text=True, timeout=30).stdout.strip()


def _find_usb_serial() -> str | None:
    """Return the first USB adb device serial (no ':' in the id = local/USB)."""
    for line in _adb("devices").splitlines()[1:]:
        parts = line.split()
        if len(parts) >= 2 and parts[1] == "device" and ":" not in parts[0]:
            return parts[0]
    return None


def _tailscale_android_ip() -> str | None:
    """Find the Android node's Tailscale IP via `tailscale status`."""
    try:
        out = subprocess.run(["tailscale", "status"], capture_output=True, text=True, timeout=20).stdout
    except Exception:  # noqa: BLE001
        return None
    for line in out.splitlines():
        parts = line.split()
        if len(parts) >= 2 and parts[0].count(".") == 3 and "android" in line.lower():
            return parts[0]
    return None


def setup(serial: str | None = None, target_ip: str | None = None, port: int = DEFAULT_PORT) -> dict:
    """Turn on wireless adb and connect over the network. Returns a status dict.

    - serial: USB device id (auto-detected when None).
    - target_ip: phone's Tailscale (or WiFi) IP; auto-detected from Tailscale when None.
    """
    serial = serial or _find_usb_serial()
    if not serial:
        return {"ok": False, "error": "no USB adb device found; plug the phone in over USB once"}

    target_ip = target_ip or _tailscale_android_ip()
    if not target_ip:
        return {"ok": False, "error": "could not determine the phone's Tailscale IP",
                "hint": "run `tailscale status`: the Android node's IP, e.g. 100.x.y.z"}

    _adb("-s", serial, "tcpip", str(port))          # phone starts listening on the network
    _adb("connect", f"{target_ip}:{port}")          # connect over the tailnet

    # Validate the wireless link really talks to the phone.
    model = _adb("-s", f"{target_ip}:{port}", "shell", "getprop", "ro.product.model").strip()
    ok = bool(model)
    return {"ok": ok, "serial": serial, "target": f"{target_ip}:{port}",
            "model": model or None,
            "next": "now unplug the USB cable — Mitchell keeps the phone over wireless",
            "hint": f"export ANDROID_SERIAL={target_ip}:{port}"}

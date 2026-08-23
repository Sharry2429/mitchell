"""Tests for Android Wireless ADB pairing and auto-sync in Mitchell."""

import pytest
from mitchell.android.adb import ADBClient
from mitchell.android.registry import device_registry, AndroidDevice


def test_adb_client_wireless_pairing_logic(monkeypatch):
    """Test USB to Wireless ADB transition workflow with mock subprocess."""
    client = ADBClient()

    # Mock devices -l command to return a USB connected phone
    def mock_run_cmd(args, timeout=15):
        cmd_str = " ".join(args)
        if "devices" in cmd_str:
            return 0, "List of devices attached\nRF8N123456X\tdevice model:Galaxy_S24 device:e3q\n", ""
        elif "ip" in cmd_str or "route" in cmd_str or "wlan0" in cmd_str:
            return 0, "192.168.1.0/24 dev wlan0 proto kernel scope link src 192.168.1.188\n", ""
        elif "tcpip" in cmd_str:
            return 0, "restarting in TCP mode port: 5555\n", ""
        elif "connect" in cmd_str:
            return 0, "connected to 192.168.1.188:5555\n", ""
        return 0, "", ""

    monkeypatch.setattr(client, "run_cmd", mock_run_cmd)

    # Execute pairing
    res = client.setup_wireless(port=5555)
    assert res["success"] is True
    assert res["wireless_serial"] == "192.168.1.188:5555"
    assert "Wireless ADB established" in res["message"]

    # Verify registered in device registry
    saved = device_registry.get("192.168.1.188:5555")
    assert saved is not None
    assert saved.is_wireless is True
    assert saved.ip_address == "192.168.1.188"

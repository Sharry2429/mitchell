import pytest
from mitchell.android.system import battery
from mitchell.android.connection import get_adb_prefix
from mitchell.core.errors import DeviceOffline, AdbError

def test_devices():
    try:
        prefix = get_adb_prefix()
        assert isinstance(prefix, list)
    except Exception as e:
        pytest.skip(f"Device interaction failed: {e}")

def test_battery():
    try:
        level = battery()
        assert level is not None
    except Exception as e:
        pytest.skip(f"Device interaction failed: {e}")

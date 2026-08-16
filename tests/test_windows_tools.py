import pytest
from mitchell.windows.apps import list_installed_apps, launch_executable
from mitchell.windows.system import get_system_info
from mitchell.windows.hardware import set_volume

def test_system_info():
    info = get_system_info()
    assert info is not None
    assert getattr(info, "cpu", None) is not None

def test_volume():
    # Only try to mute to avoid blasting sound
    assert set_volume(0) is True

def test_applications():
    apps = list_installed_apps()
    assert isinstance(apps, list)

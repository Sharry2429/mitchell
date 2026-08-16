import pytest
pytest.importorskip('sounddevice')
import json
from pathlib import Path

import pytest
import sounddevice as sd

from mitchell.voice import devices


MOCK_DEVICES = [
    {
        "name": "OnePlus Buds Pro 2 Hands-Free AG Audio",
        "max_input_channels": 1,
        "max_output_channels": 0,
        "hostapi": 0,
    },
    {
        "name": "LG TV SPDIF",
        "max_input_channels": 0,
        "max_output_channels": 2,
        "hostapi": 0,
    },
    {
        "name": "Realtek built-in mic",
        "max_input_channels": 2,
        "max_output_channels": 0,
        "hostapi": 0,
    },
    {
        "name": "Laptop speakers",
        "max_input_channels": 0,
        "max_output_channels": 2,
        "hostapi": 0,
    },
]


@pytest.fixture
def mock_sd(monkeypatch):
    """Mock sounddevice.query_devices."""
    def mock_query():
        return MOCK_DEVICES
    
    monkeypatch.setattr(devices.sd, "query_devices", mock_query)


@pytest.fixture
def mock_fs(tmp_path, monkeypatch):
    """Mock ~/.mitchell/voice configuration directory."""
    voice_dir = tmp_path / "voice"
    monkeypatch.setattr(devices, "_VOICE_DIR", voice_dir)
    monkeypatch.setattr(devices, "_DEVICE_CHOICE_PATH", voice_dir / "device_choice.json")
    return voice_dir


def test_list_devices(mock_sd):
    devs = devices.list_devices()
    assert len(devs) == 4
    
    assert devs[0]["index"] == 0
    assert devs[0]["name"] == "OnePlus Buds Pro 2 Hands-Free AG Audio"
    assert devs[0]["max_input_channels"] == 1
    assert devs[0]["max_output_channels"] == 0
    assert devs[0]["hostapi"] == 0


def test_resolve_input_device_substring(mock_sd, mock_fs):
    idx = devices.resolve_input_device("OnePlus")
    assert idx == 0
    
    idx2 = devices.resolve_input_device("realtek")
    assert idx2 == 2


def test_resolve_input_device_not_found(mock_sd, mock_fs):
    with pytest.raises(RuntimeError) as exc:
        devices.resolve_input_device("nonexistent")
    
    msg = str(exc.value)
    assert "nonexistent" in msg
    assert "OnePlus Buds Pro 2 Hands-Free AG Audio" in msg
    assert "Realtek built-in mic" in msg


def test_resolve_output_device(mock_sd, mock_fs):
    idx = devices.resolve_output_device("LG")
    assert idx == 1
    
    idx2 = devices.resolve_output_device("Laptop")
    assert idx2 == 3


def test_resolution_order(mock_sd, mock_fs, monkeypatch):
    # Priority 4: Default fallback
    assert devices.resolve_input_device() == 0  # Matches "OnePlus Buds" default
    assert devices.resolve_output_device() == 1  # Matches "LG TV" default
    
    # Priority 3: Env vars
    monkeypatch.setenv("MIC_DEVICE_NAME", "Realtek")
    monkeypatch.setenv("SPEAKER_DEVICE_NAME", "Laptop")
    
    assert devices.resolve_input_device() == 2
    assert devices.resolve_output_device() == 3
    
    # Priority 2: Saved choice overrides Env vars
    devices._save_choice(input_name="OnePlus", output_name="LG")
    
    assert devices.resolve_input_device() == 0
    assert devices.resolve_output_device() == 1
    
    # Priority 1: Argument hint overrides Saved choice
    assert devices.resolve_input_device("Realtek") == 2
    assert devices.resolve_output_device("Laptop") == 3


def test_save_load_round_trip(mock_fs):
    devices._save_choice("mic_test", "speaker_test")
    loaded = devices._load_saved_choice()
    
    assert loaded == {"input": "mic_test", "output": "speaker_test"}
    
    # Partial update - only output
    devices._save_choice(None, "speaker_new")
    loaded2 = devices._load_saved_choice()
    assert loaded2 == {"input": "mic_test", "output": "speaker_new"}
    
    # Partial update - only input
    devices._save_choice("mic_new", None)
    loaded3 = devices._load_saved_choice()
    assert loaded3 == {"input": "mic_new", "output": "speaker_new"}

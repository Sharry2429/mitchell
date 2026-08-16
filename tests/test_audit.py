import json

import pytest

from mitchell.core.audit import (
    DESTRUCTIVE,
    check_destructive,
    check_sensitive,
    get_log,
    log_action,
)
from mitchell.core.errors import RequiresConfirmation


# Mock config for testing
class MockConfig:
    def __init__(self):
        self.safeguards = True
        self.unattended_mode = False

@pytest.fixture
def mock_config(monkeypatch):
    from mitchell.core import audit
    monkeypatch.setattr(audit, "get_config", lambda: MockConfig())

@pytest.fixture
def mock_log_path(tmp_path, monkeypatch):
    log_file = tmp_path / "audit.jsonl"
    monkeypatch.setattr("mitchell.core.audit._get_log_path", lambda: log_file)
    return log_file

def test_log_action(mock_log_path):
    log_action("test_module", "test_action", {"arg1": 1}, {"kwarg1": 2}, caller="tester")
    assert mock_log_path.exists()
    
    with open(mock_log_path, "r") as f:
        data = json.loads(f.readline())
        assert data["module"] == "test_module"
        assert data["action"] == "test_action"
        assert data["args"] == "{'arg1': 1}"
        assert data["kwargs"] == "{'kwarg1': 2}"
        assert data["caller"] == "tester"

def test_check_destructive_with_confirm(mock_config):
    # Should pass without exception since confirm=True
    check_destructive(DESTRUCTIVE[0], confirm=True)

def test_check_destructive_without_confirm(mock_config):
    # Should raise RequiresConfirmation since confirm=False for a destructive action
    with pytest.raises(RequiresConfirmation):
        check_destructive(DESTRUCTIVE[0], confirm=False)

def test_check_destructive_non_destructive(mock_config):
    # Should pass since 'safe_action' is not in DESTRUCTIVE
    check_destructive("safe_action", confirm=False)

def test_check_sensitive_with_confirm(mock_config, mock_log_path):
    # 'whatsapp.read' is in SENSITIVE_READ (via 'whatsapp.')
    check_sensitive("whatsapp", "read", confirm=True)
    # Check if logged
    with open(mock_log_path, "r") as f:
        data = json.loads(f.readline())
        assert data["module"] == "whatsapp"
        assert data["action"] == "read"

def test_check_sensitive_without_confirm(mock_config, mock_log_path):
    # Should raise RequiresConfirmation
    with pytest.raises(RequiresConfirmation):
        check_sensitive("whatsapp", "read", confirm=False)

def test_check_sensitive_non_sensitive(mock_config, mock_log_path):
    check_sensitive("some_other_module", "read", confirm=False)
    with open(mock_log_path, "r") as f:
        data = json.loads(f.readline())
        assert data["module"] == "some_other_module"

def test_get_log(mock_log_path):
    log_action("m1", "a1", {}, {})
    log_action("m2", "a2", {}, {})
    
    logs = get_log()
    assert len(logs) == 2
    assert logs[0]["module"] == "m1"
    assert logs[1]["module"] == "m2"

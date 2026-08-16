from mitchell.core.config import SystemMCPConfig, configure, get_config


def test_default_config():
    # Fresh config instance
    config = SystemMCPConfig()
    assert config.unattended_mode is False
    assert config.safeguards is True
    assert config.retry_attempts == 2
    assert config.retry_delay == 0.5

def test_configure_updates_singleton():
    config = get_config()
    initial_safeguards = config.safeguards
    
    # Toggle safeguard
    configure(safeguards=not initial_safeguards)
    assert get_config().safeguards == (not initial_safeguards)
    
    # Revert
    configure(safeguards=initial_safeguards)
    assert get_config().safeguards == initial_safeguards

def test_env_override(monkeypatch):
    monkeypatch.setenv("SYSTEM_MCP_UNATTENDED", "true")
    monkeypatch.setenv("SYSTEM_MCP_SAFEGUARDS", "false")
    monkeypatch.setenv("SYSTEM_MCP_RETRY_ATTEMPTS", "5")
    monkeypatch.setenv("SYSTEM_MCP_RETRY_DELAY", "2.0")
    
    config = SystemMCPConfig.from_env()
    assert config.unattended_mode is True
    assert config.safeguards is False
    assert config.retry_attempts == 5
    assert config.retry_delay == 2.0

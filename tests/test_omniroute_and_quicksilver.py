"""Tests for OmniRoute Gateway and Hermes Agent Quicksilver Turbo Engine."""

import pytest
from mitchell.core.omniroute import OmniRouteManager
from mitchell.hive.quicksilver import HermesQuicksilverAgent, HermesQuicksilverSwarm


def test_omniroute_manager_key_loading():
    """Test OmniRoute manager auto-loads provider keys."""
    mgr = OmniRouteManager()
    keys = mgr.load_env_keys()
    assert isinstance(keys, dict)
    assert "groq" in keys
    assert "openai" in keys
    status = mgr.get_status()
    assert status.mode in ("in_process", "external_proxy")
    assert len(status.active_cascade) > 0


@pytest.mark.anyio
async def test_hermes_quicksilver_parallel_tool_execution():
    """Test Hermes Quicksilver agent risk evaluation and parallel tool dispatch."""
    agent = HermesQuicksilverAgent(agent_id="test_quicksilver_agent", model_name="fast")

    # Verify risk classifications
    safe_risk = agent.evaluate_risk("read_file", {"path": "test.txt"})
    assert safe_risk.risk_level == "safe"
    assert safe_risk.auto_approved is True

    high_risk = agent.evaluate_risk("run_command", {"command": "rm -rf /"})
    assert high_risk.risk_level == "high"
    assert high_risk.auto_approved is False

    # Test parallel tool batch execution with mocks
    tool_calls = [
        {"tool": "read_file", "arguments": {"path": "README.md"}},
        {"tool": "read_file", "arguments": {"path": "pyproject.toml"}},
    ]
    results = await agent.execute_parallel_tools(tool_calls)
    assert len(results) == 2
    assert results[0]["tool"] == "read_file"
    assert results[1]["tool"] == "read_file"


@pytest.mark.anyio
async def test_hermes_quicksilver_swarm_spawn():
    """Test spawning Hermes Quicksilver micro-swarm."""
    swarm = HermesQuicksilverSwarm()
    agent = swarm.spawn(name="turbo_reviewer", model_name="fast")
    assert agent.agent_id == "turbo_reviewer"
    assert agent.status == "ready"

"""Tests for Nous Hermes Dynamic Multi-Agent Swarm and real-time tool execution."""

import pytest
from mitchell.hive.dynamic import HermesDynamicAgent, dynamic_swarm
from mitchell.hive.router import hive_router


def test_dynamic_agent_spawn_and_destroy():
    """Test spawning dynamic agents on-the-fly and registering in Hive."""
    agent = dynamic_swarm.spawn(
        name="TestWorker_Alpha",
        description="Autonomous testing subagent",
        system_prompt="You are TestWorker_Alpha.",
        allowed_tools=["read_file"],
        model_name="fast",
    )

    assert agent.agent_id == "TestWorker_Alpha"
    assert agent.status == "idle"

    # Verify registered in HiveRouter
    found = hive_router.get_agent("TestWorker_Alpha")
    assert found is not None
    assert found.agent_id == "TestWorker_Alpha"

    # Test dynamic custom tool binding
    def custom_eval(x: int, y: int = 10):
        return x * y

    agent.bind_custom_tool("custom_eval", custom_eval)
    res = agent.execute_tool("custom_eval", {"x": 5, "y": 4})
    assert res == 20

    # Destroy agent
    destroyed = dynamic_swarm.destroy("TestWorker_Alpha")
    assert destroyed is True
    assert hive_router.get_agent("TestWorker_Alpha") is None


def test_hive_router_dynamic_listing():
    """Test HiveRouter list_agents includes dynamic agents with metadata."""
    agent = hive_router.spawn_dynamic_agent(
        name="DynamicReviewer",
        description="PR reviewer agent",
        model_name="think",
    )

    agents = hive_router.list_agents()
    dyn = [a for a in agents if a["agent_id"] == "DynamicReviewer"]
    assert len(dyn) == 1
    assert dyn[0]["is_dynamic"] is True
    assert dyn[0]["model_name"] == "think"

    # Clean up
    hive_router.destroy_dynamic_agent("DynamicReviewer")

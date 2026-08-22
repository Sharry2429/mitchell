"""Comprehensive end-to-end test suite across Phases 0 through 5 of Mitchell."""

import asyncio
from pathlib import Path
import pytest

from mitchell.core import event_log, settings
from mitchell.core.cost import cost_tracker
from mitchell.core.llm import model_router
from mitchell.core.lock import lock_manager
from mitchell.core.recovery import recovery_engine
from mitchell.core.watchdog import watchdog
from mitchell.hive import hive_router
from mitchell.manager import Manager
from mitchell.manager.classifier import goal_classifier
from mitchell.manager.council import llm_council
from mitchell.manager.critic import plan_critic
from mitchell.manager.planner import task_planner
from mitchell.memory import (
    episodic_memory,
    long_term_memory,
    self_model,
    vector_store,
)
from mitchell.skills import skill_executor, skill_learner, skill_library
from mitchell.teaching import teaching_watcher
from mitchell.tools import tool_registry


def test_phase0_foundation() -> None:
    """Verify Phase 0: Config, Event Log, Tool Registry, Hive Router, and Manager."""
    assert settings.app_name.lower() == "mitchell"
    event = event_log.log_event("test_event", source="pytest", data={"test": True})
    assert event.type == "test_event"
    assert tool_registry.get("echo") is not None
    assert hive_router.get_agent("echo_agent") is not None

    mgr = Manager()
    res = mgr.receive("help")
    assert "Available Commands:" in res


def test_phase1_browser_pillar() -> None:
    """Verify Phase 1: Browser Worker registered in Hive and auto-discovered tools."""
    assert hive_router.get_agent("browser_worker") is not None
    assert tool_registry.get("browser_goto") is not None
    assert tool_registry.get("browser_snapshot") is not None


def test_phase2_windows_and_android_pillars() -> None:
    """Verify Phase 2: Windows and Android Worker agents and tools."""
    assert hive_router.get_agent("windows_worker") is not None
    assert hive_router.get_agent("android_worker") is not None
    assert tool_registry.get("windows_launch_app") is not None
    assert tool_registry.get("android_list_devices") is not None


def test_phase3_memory_and_skills() -> None:
    """Verify Phase 3: Long-term, Episodic, Vector Store, Self-Model, and Skills."""
    # Long-term memory
    entry = long_term_memory.remember("test_cat", "test_key", "Test Memory Content")
    assert entry.content == "Test Memory Content"
    assert long_term_memory.recall("test_cat", "test_key") == "Test Memory Content"

    # Vector store search
    matches = vector_store.search("Test Memory Content", top_k=1)
    assert len(matches) > 0

    # Self-Model
    cap = self_model.record_run("test_capability", category="test", success=True, duration_s=0.5)
    assert cap.total_runs >= 1
    assert cap.success_rate == 100.0

    # Skill Library
    skills = skill_library.list_skills()
    assert len(skills) >= 2


def test_phase4_thinking_and_cost() -> None:
    """Verify Phase 4: Cost Tracker in INR, Classifier, Planner, Critic, Council, and Efficiency."""
    # Cost Tracker
    rec = cost_tracker.record_usage("grok-2", prompt_tokens=100, completion_tokens=50, purpose="test")
    assert rec.cost_inr >= 0.0
    assert not cost_tracker.is_budget_exceeded()

    # Classifier & Planner & Critic
    classification = goal_classifier.classify("Open browser and navigate to example.com")
    assert classification.domain == "browser"

    plan = asyncio.run(task_planner.create_plan("Open browser and navigate to example.com", classification))
    assert len(plan.nodes) > 0

    eval_res = plan_critic.evaluate(plan)
    assert eval_res.approved is True

    # Council
    decision = asyncio.run(llm_council.deliberate("Test topic", "Test action"))
    assert decision.consensus_decision == "APPROVED"

    # Efficiency Worker
    assert hive_router.get_agent("efficiency_worker") is not None


def test_phase5_reliability_and_teaching() -> None:
    """Verify Phase 5: Resource Locking, Checkpoints, Watchdog, and Teaching Watcher."""
    # Lock Manager
    acquired = lock_manager.acquire("res_test_1", owner_agent="agent_a", lease_seconds=10.0)
    assert acquired is True
    assert lock_manager.is_locked("res_test_1") is True
    assert lock_manager.acquire("res_test_1", owner_agent="agent_b", timeout=0.1) is False
    lock_manager.release("res_test_1", owner_agent="agent_a")
    assert lock_manager.is_locked("res_test_1") is False

    # Checkpoint Recovery
    chk = recovery_engine.create_checkpoint({"state": "active"})
    assert chk.checkpoint_id.startswith("chk_")
    report = recovery_engine.audit_and_recover()
    assert report["status"] in ("healthy", "uncompleted_tasks_detected")

    # Watchdog
    health = watchdog.run_health_check()
    assert health["database_connected"] is True
    assert health["registered_agents_count"] >= 5

    # Teaching Watcher
    teaching_watcher.start_session("taught_test_skill", description="A test skill")
    teaching_watcher.record_step("tool", "echo", {"message": "Hello World"})
    fin = teaching_watcher.finalize_skill()
    assert fin["status"] == "success"
    assert skill_library.get_skill("taught_test_skill") is not None


def test_mcp_server() -> None:
    """Verify MCP Server JSON-RPC handlers for initialize, tools/list, and tools/call."""
    from mitchell.mcp_server import MitchellMCPServer

    server = MitchellMCPServer()

    # 1. Initialize
    init_res = asyncio.run(server.handle_request({"id": 1, "method": "initialize"}))
    assert init_res["result"]["serverInfo"]["name"] == "mitchell-mcp"

    # 2. Tools List
    tools_res = asyncio.run(server.handle_request({"id": 2, "method": "tools/list"}))
    tool_names = [t["name"] for t in tools_res["result"]["tools"]]
    assert "echo" in tool_names
    assert "browser_goto" in tool_names
    assert "skill_execute" in tool_names

    # 3. Tools Call
    call_res = asyncio.run(server.handle_request({
        "id": 3,
        "method": "tools/call",
        "params": {"name": "echo", "arguments": {"message": "MCP Test Output"}},
    }))
    assert call_res["result"]["content"][0]["text"] == "MCP Test Output"


def test_deep_researcher() -> None:
    """Verify Deep Web Researcher execution and synthesis."""
    from mitchell.browser.researcher import deep_researcher

    report = asyncio.run(deep_researcher.research(topic="Artificial Intelligence", max_sources=1))
    assert report.topic == "Artificial Intelligence"
    assert len(report.key_findings) > 0
    assert len(report.sources) >= 1


def test_vision_grounding() -> None:
    """Verify Vision Grounder and Vision Worker Agent in Hive."""
    from mitchell.vision import visual_grounder
    from mitchell.hive import hive_router

    coords = visual_grounder.find_coordinates("close button")
    assert coords is not None
    assert coords[0] > 0 and coords[1] > 0

    assert hive_router.get_agent("vision_worker") is not None
    vis_res = hive_router.send_message("vision_worker", "locate search bar", sender="test")
    assert vis_res.get("status") == "success"


def test_blackboard_and_teams() -> None:
    """Verify Shared Blackboard, Team Coordinator, and TaskGraphScheduler."""
    from mitchell.hive.blackboard import blackboard
    from mitchell.hive.teams import team_coordinator
    from mitchell.hive.tasks import task_scheduler
    from mitchell.manager.planner import TaskGraph, TaskNode

    # 1. Blackboard
    entry = blackboard.post("test_topic", {"key": "value"}, author="tester")
    assert entry.topic == "test_topic"
    entries = blackboard.read_topic("test_topic")
    assert len(entries) >= 1

    # 2. Team Coordinator
    assert len(team_coordinator.list_teams()) >= 3
    res = team_coordinator.dispatch_team("optimization_team", "audit")
    assert res.get("status") == "success"

    # 3. TaskGraph Scheduler
    node1 = TaskNode(title="Step 1", target_agent="echo_agent", action="Hello 1")
    node2 = TaskNode(title="Step 2", target_agent="echo_agent", action="Hello 2", dependencies=[node1.id])
    graph = TaskGraph(goal="Test multi-node DAG", nodes=[node1, node2])

    exec_res = asyncio.run(task_scheduler.execute_graph(graph))
    assert exec_res.success is True
    assert exec_res.nodes_completed == 2


def test_voice_subsystem() -> None:
    """Verify cross-platform voice STT, TTS, and VoiceMode modules import and initialize."""
    import sys
    from mitchell.voice.stt import SpeechToText, stt_engine
    from mitchell.voice.tts import TextToSpeech, tts_engine
    from mitchell.voice.voice_mode import VoiceMode, voice_mode

    # STT should always instantiate
    assert isinstance(stt_engine, SpeechToText)

    # TTS should pick a backend (even if console fallback)
    assert isinstance(tts_engine, TextToSpeech)
    assert tts_engine._backend in ("pyttsx3", "macos_say", "espeak", "console", "none")

    # VoiceMode should be constructable
    assert isinstance(voice_mode, VoiceMode)
    assert voice_mode.is_active is False


def test_cross_platform_guards() -> None:
    """Verify Windows-only modules gracefully handle non-Windows platforms."""
    import sys

    # Windows mouse should always import without error
    from mitchell.windows.mouse import DesktopMouse, desktop_mouse
    assert isinstance(desktop_mouse, DesktopMouse)

    # Windows engine should import without error
    from mitchell.windows.engine import WindowsEngine, windows_engine
    assert isinstance(windows_engine, WindowsEngine)

    # On non-Windows, pywinauto won't be available but should not crash
    if sys.platform != "win32":
        from mitchell.windows.engine import PYWINAUTO_AVAILABLE
        assert PYWINAUTO_AVAILABLE is False






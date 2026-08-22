"""Comprehensive end-to-end test suite across Phases 0 through 5 of Mitchell."""

import asyncio
from pathlib import Path
from typing import Any, Dict, List, Optional
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


def test_self_evolution_engine() -> None:
    """Verify code inspection, safety gating, dynamic tool synthesis, and registration."""
    from mitchell.evolution import code_inspector, tool_synthesizer, evolution_engine
    from mitchell.tools.registry import tool_registry

    # 1. Codebase Introspection
    summary = code_inspector.get_system_summary()
    assert summary["total_source_files"] > 15
    assert summary["total_registered_tools"] >= 4

    # 2. Safety Invariant Check
    is_safe, err = tool_synthesizer.check_safety_invariants("import os; os.system('rm -rf /')")
    assert is_safe is False
    assert "Safety invariant violation" in str(err)

    # 3. Dynamic Tool Synthesis
    synth_fn_code = "def custom_hash_calculator(text: str) -> str:\n    import hashlib\n    return hashlib.md5(text.encode()).hexdigest()\n"
    res = tool_synthesizer.synthesize_tool(
        name="custom_hash_calculator",
        description="Calculates MD5 hash of input text.",
        parameters={"type": "object", "properties": {"text": {"type": "string"}}},
        function_code=synth_fn_code,
    )
    assert res["status"] == "success"

    # Verify tool callable from ToolRegistry
    calc_tool = tool_registry.get("custom_hash_calculator")
    assert calc_tool is not None
    hash_output = calc_tool.function("hello mitchell")
    assert len(hash_output) == 32


def test_daemon_queue_and_cron() -> None:
    """Verify daemon persistent queue, priority ordering, and cron scheduler."""
    import datetime
    from mitchell.daemon import daemon_queue, cron_scheduler, daemon_sentinel

    # 1. Priority Queue
    t1 = daemon_queue.enqueue(goal="Low priority routine", priority=5)
    t2 = daemon_queue.enqueue(goal="Critical emergency fix", priority=50)

    # Higher priority must dequeue first
    first_task = daemon_queue.dequeue()
    assert first_task is not None
    assert first_task["id"] == t2
    daemon_queue.complete_task(task_id=first_task["id"], result={"done": True})

    # 2. Cron Scheduler
    now = datetime.datetime.now()
    cron_expr = f"{now.minute} {now.hour} * * *"
    cron_scheduler.add_job(job_id="test_minutely", cron_expr=cron_expr, goal="Check system load")
    triggered = cron_scheduler.tick(now_dt=now)
    assert "test_minutely" in triggered
    cron_scheduler.remove_job("test_minutely")

    # 3. Sentinel
    health = daemon_sentinel.check_system_health()
    assert health["status"] in ("healthy", "degraded")


def test_local_llm_and_notifications() -> None:
    """Verify local LLM offline fallback and multi-channel notifier."""
    from mitchell.core.local_llm import local_llm
    from mitchell.gateways import notifier

    # Offline LLM fallback
    resp = local_llm.generate("Hello Mitchell Offline")
    assert "text" in resp

    # Notifier
    notif_res = notifier.notify_all("System Alert", "Mitchell Phase 10 tests running.")
    assert "desktop" in notif_res


def test_universal_mcp_client() -> None:
    """Verify external MCP client bridge, tool discovery, and tool execution."""
    from mitchell.mcp_client import MCPClientHub
    from mitchell.tools.registry import tool_registry

    hub = MCPClientHub()
    client = hub.register_client(
        server_name="github_mock",
        tools_dict={
            "get_repo": {
                "description": "Get repo details",
                "parameters": {"type": "object", "properties": {"repo": {"type": "string"}}},
                "handler": lambda repo: f"Mock repo details for {repo}",
            }
        },
    )

    assert client.is_connected is True
    assert "get_repo" in client.list_remote_tools()

    # Tool should be registered into Mitchell's ToolRegistry
    bridged_tool = tool_registry.get("mcp_github_mock_get_repo")
    assert bridged_tool is not None
    exec_res = bridged_tool.function(repo="Sharry2429/mitchell")
    assert exec_res["status"] == "success"
    assert "Mock repo details" in exec_res["result"]


def test_distributed_mesh_coordinator() -> None:
    """Verify mesh node registration, capability matching, and remote dispatch."""
    from mitchell.mesh import MeshCoordinator, MeshNode, MeshTaskRequest

    coord = MeshCoordinator()
    satellite = MeshNode(
        node_id="linux_gpu_worker",
        node_name="Ubuntu-RTX4090",
        capabilities=["linux_cli", "gpu", "local_llm"],
    )
    coord.register_node(satellite)

    nodes = coord.list_nodes()
    assert len(nodes) >= 2

    # Capability matching
    matched_id = coord.find_node_for_capability("gpu")
    assert matched_id == "linux_gpu_worker"

    # Dispatch remote task
    req = MeshTaskRequest(
        target_node_id="linux_gpu_worker",
        goal="echo remote mesh task",
    )
    res = coord.dispatch_task(req)
    assert res.status == "success"
    assert res.node_id == "linux_gpu_worker"


def test_dynamic_plugin_loader(tmp_path: Any) -> None:
    """Verify plugin manifest validation, dynamic module execution, and tool registration."""
    import json
    from mitchell.plugins import PluginLoader
    from mitchell.tools.registry import tool_registry

    plugin_dir = tmp_path / "sample_crypto_plugin"
    plugin_dir.mkdir()

    manifest_json = {
        "name": "crypto_helper",
        "version": "1.0.0",
        "description": "Calculates SHA512 hashes",
        "entry_point": "plugin.py",
    }
    (plugin_dir / "plugin.json").write_text(json.dumps(manifest_json), encoding="utf-8")

    plugin_py = (
        "from mitchell.tools.registry import Tool\n"
        "import hashlib\n"
        "def sha512_calc(text: str) -> str:\n"
        "    return hashlib.sha512(text.encode()).hexdigest()\n"
        "TOOLS = [\n"
        "    Tool(name='calc_sha512', description='SHA512 calculator', parameters={'type':'object','properties':{'text':{'type':'string'}}}, function=sha512_calc)\n"
        "]\n"
    )
    (plugin_dir / "plugin.py").write_text(plugin_py, encoding="utf-8")

    loader = PluginLoader(plugins_dir=tmp_path)
    loaded = loader.discover_and_load_all()
    assert len(loaded) == 1
    assert loaded[0].name == "crypto_helper"

    # Tool should be registered
    plugin_tool = tool_registry.get("calc_sha512")
    assert plugin_tool is not None
    assert len(plugin_tool.function("test")) == 128


def test_studio_state_provider() -> None:
    """Verify studio state aggregation across blackboard, cost, and event log."""
    from mitchell.studio.server import studio_state

    state = studio_state.get_full_state()
    assert "blackboard" in state
    assert "cost" in state
    assert "recent_events" in state


def test_benchmark_arena_runner() -> None:
    """Verify benchmark scenario execution, scorecard metrics, and markdown leaderboard formatting."""
    from mitchell.benchmark import BenchmarkRunner, BenchmarkScenario

    custom_scenario = BenchmarkScenario(
        id="bench_test_echo",
        title="Simple Test Evaluation",
        domain="reasoning",
        goal="echo benchmark verification",
        difficulty="easy",
    )

    runner = BenchmarkRunner()
    scorecard = runner.run_suite(scenarios=[custom_scenario])
    summary = scorecard.get_summary()

    assert summary["total_scenarios"] == 1
    assert summary["passed"] == 1
    assert summary["pass_rate_pct"] == 100.0

    report = scorecard.generate_markdown_report()
    assert "# 🏆 Mitchell Autonomous Agent Benchmark Scorecard" in report
    assert "bench_test_echo" in report









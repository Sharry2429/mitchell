"""Tests for WhatsApp MCP integration, dynamic system prompts, Hive worker agents, and system refinements."""

import os
from pathlib import Path
import pytest

from mitchell.comms import (
    communication_hub,
    whatsapp_bridge,
    whatsapp_mcp,
)
from mitchell.comms.whatsapp_mcp import WhatsAppMCPBridge
from mitchell.core.llm import (
    KARPATHY_SYSTEM_PROMPT,
    MITCHELL_CORE_SYSTEM_PROMPT,
    MITCHELL_CRITIC_SYSTEM_PROMPT,
    MITCHELL_PLANNER_SYSTEM_PROMPT,
    build_dynamic_system_prompt,
    model_router,
)
from mitchell.hive.router import hive_router
from mitchell.manager.classifier import goal_classifier
from mitchell.manager.intent import parse_fast_intent
from mitchell.manager.loop import Manager
from mitchell.manager.planner import task_planner
from mitchell.mcp_client.hub import mcp_hub
from mitchell.tools.registry import tool_registry


def test_whatsapp_mcp_integration() -> None:
    """Verify WhatsApp MCP bridge (https://github.com/lharries/whatsapp-mcp) tools and hub registration."""
    # 1. Verify registered in MCP Hub
    client = mcp_hub.get_client("whatsapp_mcp")
    assert client is not None
    assert client.is_connected is True
    assert "send_message" in client.list_remote_tools()
    assert "list_chats" in client.list_remote_tools()
    assert "list_messages" in client.list_remote_tools()

    # 2. Test send_message
    res = whatsapp_mcp.send_message(recipient="+14155552671", message="Hello from Mitchell Peak WhatsApp MCP")
    assert res["status"] == "success"
    assert res["provider"] == "whatsapp-mcp"
    assert res["recipient"] == "+14155552671"

    # 3. Test list_chats & list_messages
    chats = whatsapp_mcp.list_chats(limit=10)
    assert len(chats) > 0

    msgs = whatsapp_mcp.list_messages(chat_jid="+14155552671", limit=5)
    assert len(msgs) > 0

    # 4. Test search contacts
    contacts = whatsapp_mcp.search_contacts("14155552671")
    assert len(contacts) > 0


def test_dynamic_system_prompts_and_karpathy_rigor() -> None:
    """Verify calibrated Karpathy system prompts and dynamic context builder."""
    assert "THINK BEFORE ACTING" in MITCHELL_CORE_SYSTEM_PROMPT
    assert "SIMPLICITY FIRST" in MITCHELL_CORE_SYSTEM_PROMPT
    assert "SURGICAL CHANGES" in MITCHELL_CORE_SYSTEM_PROMPT
    assert "GOAL-DRIVEN EXECUTION" in MITCHELL_CORE_SYSTEM_PROMPT
    assert KARPATHY_SYSTEM_PROMPT == MITCHELL_CORE_SYSTEM_PROMPT

    dynamic_prompt = build_dynamic_system_prompt(
        include_user_model=True,
        include_procedures=True,
        include_tools=True,
    )
    assert "You are Mitchell" in dynamic_prompt
    assert "Available Native Tools" in dynamic_prompt


def test_hive_worker_agents_registration_and_execution() -> None:
    """Verify that all specialized Hive worker agents are registered and process messages."""
    agents = hive_router.list_agents()
    agent_ids = [a["agent_id"] for a in agents]

    expected_agents = [
        "browser_worker",
        "windows_worker",
        "android_worker",
        "workspace_worker",
        "ide_worker",
        "comms_worker",
        "media_worker",
        "commerce_worker",
        "iot_worker",
    ]
    for expected in expected_agents:
        assert expected in agent_ids

    # Dispatch to Workspace Worker
    ws_res = hive_router.send_message(
        agent_id="workspace_worker",
        message={"action": "document", "title": "Test Doc", "content": "Hello World"},
    )
    assert ws_res["status"] == "success"

    # Dispatch to Comms Worker (WhatsApp MCP)
    comms_res = hive_router.send_message(
        agent_id="comms_worker",
        message={"action": "whatsapp", "recipient": "+19998887777", "message": "Test via Hive"},
    )
    assert comms_res["status"] == "success"

    # Dispatch to Media Worker
    media_res = hive_router.send_message(
        agent_id="media_worker",
        message={"action": "spotify", "query": "synthwave"},
    )
    assert media_res["status"] == "success"


def test_manager_fast_intents_and_task_planning() -> None:
    """Verify Manager fast intent shortcuts and multi-domain plan formulation."""
    # Fast WhatsApp shortcut
    intent_wa = parse_fast_intent("whatsapp +1234567890 Meeting in 5 minutes")
    assert intent_wa is not None
    assert intent_wa.action_type == "call_tool"
    assert intent_wa.tool_name == "comms_send_whatsapp"
    assert intent_wa.parameters["phone_number"] == "+1234567890"

    # Fast Spotify shortcut
    intent_spot = parse_fast_intent("spotify lofi beats")
    assert intent_spot is not None
    assert intent_spot.action_type == "call_tool"
    assert intent_spot.tool_name == "media_play_spotify"

    # Goal Classifier across all domains
    c_ws = goal_classifier.classify("create spreadsheet for Q3 expenses")
    assert c_ws.domain == "workspace"

    c_ide = goal_classifier.classify("run pytest on user authentication suite")
    assert c_ide.domain == "ide"

    c_iot = goal_classifier.classify("turn on living room light and activate cinema mode")
    assert c_iot.domain in ("iot", "multi_pillar")


@pytest.mark.anyio
async def test_end_to_end_manager_loop_execution() -> None:
    """Verify complete Manager Decision Loop end-to-end with dynamic planning."""
    manager = Manager()

    # Fast intent path
    res_help = manager.receive("help")
    assert "Available Commands" in res_help

    # Fast WhatsApp intent execution
    res_wa = manager.receive("whatsapp +14155550000 Status update complete")
    assert "[Tool: comms_send_whatsapp]" in res_wa

    # Fast Telemetry intent execution
    res_telem = manager.receive("telemetry")
    assert "[Tool: system_get_telemetry]" in res_telem

    # Fast Briefing intent execution
    res_briefing = manager.receive("briefing")
    assert "[Tool: system_generate_briefing]" in res_briefing

    # Planner path
    res_plan = manager.receive("create document titled Architecture Brief with content System Architecture Overview")
    assert "Architecture Brief" in res_plan or "success" in res_plan.lower()


@pytest.mark.anyio
async def test_dynamic_system_telemetry_and_briefing() -> None:
    """Verify live dynamic system telemetry and AI-synthesized briefing generation."""
    from mitchell.system import dynamic_briefing, live_system_monitor

    # Live telemetry
    metrics = live_system_monitor.get_live_metrics()
    assert metrics.os_name != ""
    assert metrics.ram_total_gb > 0
    assert metrics.disk_total_gb > 0
    assert metrics.uptime_seconds >= 0

    summary = live_system_monitor.format_summary()
    assert "CPU:" in summary
    assert "RAM:" in summary

    # Dynamic briefing
    briefing = await dynamic_briefing.generate_dynamic_briefing(user_name="Mitchell Developer", use_llm=False)
    assert "Mitchell AI Intelligence Briefing" in briefing.title
    assert "Hardware:" in briefing.executive_synthesis
    assert briefing.spoken_summary != ""

    md = dynamic_briefing.format_markdown(briefing)
    assert "Live Hardware Telemetry" in md
    assert "Mitchell AI Executive Synthesis" in md

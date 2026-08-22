"""Comprehensive integration test suite validating the MitchellAI Final Peak capabilities."""

import os
import tempfile
from datetime import datetime, timezone, timedelta
from pathlib import Path
import pytest

from mitchell.commerce import commerce_assistant, commerce_search, price_tracker
from mitchell.comms import communication_hub, message_scheduler, sms_manager, whatsapp_bridge
from mitchell.core.config import settings
from mitchell.core.llm import model_router
from mitchell.core.providers import provider_registry
from mitchell.core.recovery import recovery_engine
from mitchell.crossdevice import (
    continuity_engine,
    cross_device_clipboard,
    device_pairing_manager,
    file_transfer_engine,
    phone_link_bridge,
    screen_mirror_engine,
)
from mitchell.ide import code_editor, code_runner, git_manager, platform_bridges, project_scaffolder, terminal_manager
from mitchell.iot import homeassistant_client, smart_device_controller, smart_scene_engine
from mitchell.media import download_manager, media_player, media_recommender, spotify_controller
from mitchell.memory.consolidator import medium_term_memory, memory_consolidator
from mitchell.memory.self_model import self_model
from mitchell.tools.registry import tool_registry
from mitchell.workspace import (
    calendar_engine,
    document_engine,
    mail_engine,
    notes_engine,
    project_engine,
    spreadsheet_engine,
    workspace_manager,
    workspace_storage,
    workspace_sync,
)


def test_provider_registry_and_cascade() -> None:
    """Verify multi-provider registry, health scoring, and free-tier cascade order."""
    providers = provider_registry.list_providers()
    assert len(providers) >= 7
    assert any(p["name"] == "groq" for p in providers)
    assert any(p["name"] == "nvidia_nim" for p in providers)

    cascade = provider_registry.get_cascade_order(prefer_free=True)
    assert len(cascade) >= 1
    # First provider in prefer_free mode should be a free-tier provider
    assert cascade[0][0].is_free_tier is True


def test_user_model_and_procedural_memory() -> None:
    """Verify user model preference storage, contradiction tracking, and procedural memory."""
    # User model
    pref1 = self_model.set_user_preference(key="editor_theme", value="dark", category="preference")
    assert pref1.value == "dark"

    pref2 = self_model.set_user_preference(key="editor_theme", value="light", category="preference")
    assert pref2.contradicted_by == "dark"

    # Procedural memory
    proc = self_model.store_procedure(
        name="deploy_preview",
        description="Deploy preview branch",
        steps=[{"step": 1, "action": "build"}, {"step": 2, "action": "deploy"}],
        trigger_pattern="deploy preview",
    )
    assert proc.name == "deploy_preview"
    assert len(proc.steps) == 2

    found = self_model.find_procedures("deploy")
    assert len(found) >= 1


def test_memory_consolidation_and_medium_term() -> None:
    """Verify medium-term memory buffer, importance scoring, and consolidation."""
    mem_id = medium_term_memory.store(
        content="Important deployment rule: always verify build before committing",
        importance=0.9,
    )
    assert mem_id is not None

    important = medium_term_memory.get_important(threshold=0.8)
    assert any(m["id"] == mem_id for m in important)

    res = memory_consolidator.run_consolidation()
    assert res["status"] == "success"


def test_recovery_engine_and_diagnostics() -> None:
    """Verify novel failure recording, repair suggestions, and self-diagnostics."""
    err = ConnectionError("Failed to reach external API endpoint")
    pattern = recovery_engine.record_failure(error=err, component="provider_llm")
    assert pattern.error_type == "ConnectionError"
    assert "network" in pattern.suggested_fix.lower() or "retry" in pattern.suggested_fix.lower()

    diag = recovery_engine.run_diagnostics()
    assert diag.overall_health in ("healthy", "degraded", "critical")
    assert diag.uptime_seconds >= 0


def test_workspace_documents_and_storage() -> None:
    """Verify document creation, versioning, outline generation, and HTML export."""
    doc = document_engine.create_document(
        title="Peak Architecture Plan",
        initial_content="# Peak Architecture\n\n## Overview\nMitchell native workspace test.\n\n## Pillars\n- Browser\n- Windows\n- Android\n",
    )
    assert doc.doc_id == "peak_architecture_plan"
    outline = doc.get_outline()
    assert len(outline) == 3
    assert outline[0]["title"] == "Peak Architecture"

    html = doc.to_html()
    assert "<h1>Peak Architecture</h1>" in html

    # Verify storage versioning
    files = workspace_storage.list_files(sub_dir="documents")
    assert any(f["name"] == "peak_architecture_plan.md" for f in files)


def test_workspace_spreadsheet_formulas() -> None:
    """Verify spreadsheet creation, formula evaluation (SUM, AVG, IF), and CSV export."""
    sheet = spreadsheet_engine.create_sheet("Financial_Forecast")
    sheet.set_cell("A1", 100)
    sheet.set_cell("A2", 200)
    sheet.set_cell("A3", 300)
    sheet.set_cell("A4", "=SUM(A1:A3)")
    sheet.set_cell("B1", "=AVG(A1:A3)")
    sheet.set_cell("C1", "=IF(A4 > 500, High, Low)")

    sheet.evaluate_all()
    assert sheet.get_cell_value("A4") == 600
    assert sheet.get_cell_value("B1") == 200
    assert sheet.get_cell_value("C1") == "High"

    csv_data = sheet.to_csv()
    assert "100" in csv_data
    assert "600" in csv_data

    stats = sheet.get_column_stats("A")
    assert stats["count"] == 4  # A1, A2, A3, A4
    assert stats["mean"] == 300.0


def test_workspace_notes_and_knowledge_graph() -> None:
    """Verify linked notes, [[WikiLink]] extraction, backlinks, and graph generation."""
    notes_engine.create_note("Quantum Computing", "# Quantum Computing\n\nRelated to [[Linear Algebra]] and [[Qubits]].")
    notes_engine.create_note("Linear Algebra", "# Linear Algebra\n\nMathematical foundation.")

    graph = notes_engine.get_knowledge_graph()
    assert len(graph["nodes"]) >= 2
    assert any(link["target"] == "Linear Algebra" for link in graph["links"])


def test_workspace_projects_and_kanban() -> None:
    """Verify project board creation, task columns, status updates, and progress metrics."""
    board = project_engine.create_board("Mitchell Peak Release", "2026 Practical Maximum")
    t1 = board.add_task(title="Build Native Workspace", status="done")
    t2 = board.add_task(title="Refactor Studio UI", status="in_progress")
    t3 = board.add_task(title="Deploy Release", status="todo")

    prog = board.get_progress()
    assert prog["total"] == 3
    assert prog["completed"] == 1
    assert prog["percent"] == 33.3

    cols = board.get_column_view()
    assert len(cols["done"]) == 1
    assert len(cols["in_progress"]) == 1


def test_agentic_ide_scaffolding_and_editor() -> None:
    """Verify project scaffolding, file reading, unified diff patching, and AST syntax checks."""
    import time
    proj_name = f"Test_App_{int(time.time()*1000)}"
    manifest = project_scaffolder.create_project(name=proj_name, template="python")
    assert manifest.name == proj_name
    assert (Path(manifest.root_path) / "main.py").exists()

    # Edit file with syntax verification
    res = code_editor.write_file(
        file_path=str(Path(manifest.root_path) / "main.py"),
        content='"""Updated entry."""\n\ndef run() -> None:\n    print("Success")\n',
    )
    assert res.success is True
    assert res.syntax_valid is True
    assert res.lines_added > 0


def test_cross_device_and_comms_subsystems() -> None:
    """Verify cross-device clipboard, device registry, continuity, and comms hub."""
    # Clipboard
    clip = cross_device_clipboard.set_clipboard("https://github.com/mitchell-ai")
    assert clip.text == "https://github.com/mitchell-ai"

    # Continuity
    handoff = continuity_engine.handoff_url_to_mobile("https://arxiv.org/abs/2310.00001")
    assert handoff.payload["url"] == "https://arxiv.org/abs/2310.00001"

    # Comms Hub
    msg = communication_hub.record_message(
        channel="whatsapp",
        sender="+1234567890",
        recipient="me",
        content="Meeting rescheduled to 3 PM",
    )
    assert msg.channel == "whatsapp"
    results = communication_hub.search_all_channels("Meeting")
    assert len(results) >= 1


def test_media_commerce_and_iot() -> None:
    """Verify media playback, download manager, commerce price tracking, and IoT scenes."""
    # Media
    player_state = media_player.play("Interstellar Soundtrack", source="spotify")
    assert player_state.is_playing is True

    # Download manager
    dl = download_manager.add_download("https://example.com/test.zip", "test.zip")
    assert dl.file_name == "test.zip"

    # Commerce price tracker
    item = price_tracker.track_product(
        title="Ergonomic Mechanical Keyboard",
        current_price=7999.0,
        target_price=6999.0,
        url="https://amazon.in/dp/B000000",
    )
    assert item.target_price_inr == 6999.0

    # IoT Scene
    scene = smart_scene_engine.SCENES.get("cinema_mode")
    assert scene is not None
    assert len(scene["actions"]) >= 2


def test_tool_registry_auto_discovery() -> None:
    """Verify that all new tools across workspace, ide, crossdevice, comms, media, commerce, and iot are registered."""
    tool_names = [t["name"] for t in tool_registry.list_tools()]
    assert "workspace_get_summary" in tool_names
    assert "workspace_document_create" in tool_names
    assert "ide_terminal_run" in tool_names
    assert "crossdevice_send_sms" in tool_names
    assert "crossdevice_set_clipboard" in tool_names
    assert "comms_send_whatsapp" in tool_names
    assert "media_play_spotify" in tool_names
    assert "commerce_search_products" in tool_names
    assert "iot_activate_smart_scene" in tool_names
    assert len(tool_names) >= 40

"""
Tool-surface registration test (Phase 8 — Windows + browser).
No network, no device execution: verifies the unified MCP surface exposes the
Windows, browser, and core tool families.
"""
import asyncio

import mitchell.mcp_server as s


def registered_tools():
    """Collect the names of all MCP tools already registered on the server."""
    async def _go():
        return sorted(t.name for t in await s.mcp.list_tools())
    return asyncio.run(_go())


def test_windows_tools_registered():
    names = registered_tools()
    assert any(n.startswith("windows_system_") for n in names)
    assert any(n.startswith("windows_ui_") for n in names)
    assert any(n.startswith("windows_hardware_") for n in names)
    assert any(n.startswith("windows_apps_") for n in names)


def test_browser_tools_registered_clean_names():
    names = registered_tools()
    # Clean names, no triple platform/module prefix, no import leaked as a tool.
    assert "browser_navigate" in names
    assert "browser_extract_text" in names
    assert "browser_title" in names
    assert "browser_stop" in names
    assert not any("async_playwright" in n for n in names)
    assert not any(n.count("browser") > 2 for n in names)


def test_core_memory_tools_registered():
    names = registered_tools()
    assert "core_memory_log_episode" in names
    assert "core_memory_promote_verified_patterns" in names
    assert "core_verify_verify_step" in names

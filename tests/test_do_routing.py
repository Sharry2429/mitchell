"""
Session goal: Hermes-Agent as Mitchell's coding worker + fast interface.
Lightweight (no paid Hermes spawn): intent routing, safe allowlist, and
MCP registration. Real delegation is proven live in scripts/run_autonomous
and the `mitchell do` fast path.
"""
import asyncio

from mitchell.core.routing import _is_coding
from mitchell.core.safe_provider import is_safe


def test_intent_routing():
    assert _is_coding("implement a function double(x)")
    assert _is_coding("write a python script that parses csv")
    assert not _is_coding("open example.com and report the title")
    assert not _is_coding("check the android battery")


def test_safe_allowlist_blocks_destructive():
    assert is_safe("windows_system_get_cpu_info")
    assert is_safe("browser_navigate")
    assert is_safe("coding_implement")
    # Destructive / irreversible actions are NOT exposed to autonomous executors.
    assert not is_safe("windows_system_shutdown")
    assert not is_safe("windows_system_kill")
    assert not is_safe("android_apps_uninstall")
    assert not is_safe("android_communication_send")
    assert not is_safe("windows_system_reg_write")


def test_coding_tool_registered_on_mcp_surface():
    import mitchell.mcp_server as s

    async def _names():
        return [t.name for t in await s.mcp.list_tools()]

    names = asyncio.run(_names())
    assert "coding_implement" in names

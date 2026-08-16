"""
Hermes tool gateway — Mitchell can call "all the tools Hermes has".

Lightweight (no paid Hermes spawn): manifest integrity, safe-allowlisting, and
MCP surface registration. Live delegation is proven in scripts and the
`hermes_terminal`/`hermes_web` calls.
"""
import asyncio

from mitchell.coding import hermes_gateway as hg
from mitchell.core.safe_provider import is_safe


def test_manifest_names_map_to_callables():
    defined = {"hermes_agent", "hermes_web", "hermes_terminal", "hermes_file",
               "hermes_browser", "hermes_vision", "hermes_memory", "hermes_skills"}
    for tool_name, flag, desc in hg.MANIFEST:
        assert flag  # toolset flag present
        assert desc  # description present
        if tool_name in defined:
            assert callable(getattr(hg, tool_name))


def test_hermes_tools_allowed_in_fast_path():
    assert is_safe("hermes_agent")
    assert is_safe("hermes_terminal")
    assert is_safe("hermes_web")
    assert is_safe("hermes_file")


def test_hermes_tools_registered_on_mcp_surface():
    import mitchell.mcp_server as s

    async def _names():
        return [t.name for t in await s.mcp.list_tools()]

    names = asyncio.run(_names())
    assert "hermes_agent" in names
    assert "hermes_terminal" in names
    assert "hermes_web" in names

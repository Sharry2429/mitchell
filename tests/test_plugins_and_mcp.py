"""Comprehensive unit and integration test suite for Plugins, Marketplaces, Skills, and MCP Client."""

import json
from pathlib import Path
import pytest

from mitchell.manager.intent import parse_fast_intent
from mitchell.mcp_client.client import MCPClient
from mitchell.mcp_client.hub import MCPClientHub, mcp_hub
from mitchell.plugins.installer import PluginInstaller, plugin_installer
from mitchell.plugins.loader import PluginLoader, plugin_loader
from mitchell.plugins.manifest import PluginManifest
from mitchell.plugins.marketplace import PluginMarketplace, plugin_marketplace
from mitchell.skills.executor import skill_executor
from mitchell.skills.library import skill_library
from mitchell.skills.parser import SkillMarkdownParser
from mitchell.skills.schema import Skill, SkillStep
from mitchell.tools.plugin_tools import (
    tool_mcp_add_server,
    tool_mcp_call_tool,
    tool_mcp_list_servers,
    tool_mcp_remove_server,
    tool_plugin_install,
    tool_plugin_list,
    tool_plugin_uninstall,
    tool_skill_execute,
    tool_skill_install,
    tool_skill_list,
)
from mitchell.tools.registry import Tool, tool_registry


# ── 1. Plugin Manifest & Loader Tests ─────────────────────────────────────────

def test_plugin_manifest_claude_compat():
    """Verify PluginManifest supports Claude Code manifest format and author parsing."""
    claude_data = {
        "name": "test-claude-plugin",
        "version": "2.0.0",
        "description": "Claude compatible test plugin",
        "author": {"name": "Anthropic Partner"},
        "skills": "skills/",
        "mcp_servers": {"local_mcp": {"command": "echo", "args": ["hello"]}},
        "tags": ["test", "claude"],
    }
    manifest = PluginManifest.model_validate(claude_data)
    assert manifest.name == "test-claude-plugin"
    assert manifest.author == "Anthropic Partner"
    assert manifest.version == "2.0.0"
    assert manifest.mcp_servers is not None
    assert "local_mcp" in manifest.mcp_servers


def test_plugin_marketplace_catalog():
    """Verify official catalog contains top Claude plugins."""
    market = PluginMarketplace()
    catalog = market.catalog
    assert "github" in catalog
    assert "sqlite" in catalog
    assert "fetch" in catalog
    assert "memory" in catalog
    assert "docker" in catalog
    assert "postgresql" in catalog

    # Search
    dev_plugins = market.search_catalog(category="dev")
    assert any(p.name == "github" for p in dev_plugins)

    # Keyword search
    sql_plugins = market.search_catalog(query="sqlite")
    assert len(sql_plugins) >= 1
    assert sql_plugins[0].name == "sqlite"


# ── 2. Plugin Installer & Loader Integration Tests ────────────────────────────

def test_plugin_installer_and_discovery(tmp_path):
    """Test installing a marketplace plugin, loading its skills and tools."""
    installer = PluginInstaller(plugins_dir=tmp_path)
    res = installer.install("sqlite")
    assert res["success"] is True
    assert "sqlite" in res["message"]

    plugin_dir = tmp_path / "sqlite"
    assert plugin_dir.exists()
    assert (plugin_dir / "plugin.json").exists()
    assert (plugin_dir / ".claude-plugin" / "plugin.json").exists()
    assert (plugin_dir / "skills" / "SKILL.md").exists()

    # Discover and load
    loader = PluginLoader(plugins_dir=tmp_path)
    loaded = loader.discover_and_load_all()
    assert any(p.name == "sqlite" for p in loaded)

    # Uninstall
    un_res = installer.uninstall("sqlite")
    assert un_res["success"] is True
    assert not plugin_dir.exists()


# ── 3. SKILL.md Markdown Parser & Library Tests ──────────────────────────────

def test_skill_markdown_parser():
    """Test parsing and serializing SKILL.md with YAML frontmatter."""
    sample_md = """---
name: custom_data_pipeline
version: 1.5.0
description: Transform raw dataset into structured metrics.
tags:
  - analytics
  - data
required_tools:
  - system_get_telemetry
---

# Custom Data Pipeline

Detailed execution instructions.

## Execution Steps
1. Fetch system status: `system_get_telemetry()`
2. Process metrics: `prompt`
"""
    skill = SkillMarkdownParser.parse_text(sample_md)
    assert skill.name == "custom_data_pipeline"
    assert skill.version == "1.5.0"
    assert "analytics" in skill.tags
    assert len(skill.steps) == 2
    assert skill.steps[0].target == "system_get_telemetry"

    # Serialize back
    serialized = SkillMarkdownParser.serialize_to_markdown(skill)
    assert "custom_data_pipeline" in serialized
    assert "system_get_telemetry" in serialized


def test_skill_library_markdown_install_and_exec():
    """Test installing a markdown skill directly into SkillLibrary and executing it."""
    md = """---
name: test_library_proc_skill
version: 1.0.0
description: Fast mock procedural skill
tags: [testing]
---
1. Check hardware: `system_get_telemetry()`
"""
    skill = skill_library.install_skill_markdown(md, name="test_library_proc_skill")
    assert skill.name == "test_library_proc_skill"

    # Retrieve
    retrieved = skill_library.get_skill("test_library_proc_skill")
    assert retrieved is not None

    # Execute
    res = skill_executor.execute("test_library_proc_skill")
    assert res["success"] is True
    assert len(res["steps"]) == 1

    # Cleanup
    assert skill_library.delete_skill("test_library_proc_skill") is True
    assert skill_library.get_skill("test_library_proc_skill") is None


# ── 4. MCP Client & Hub Tests ────────────────────────────────────────────────

def test_mcp_client_inprocess_bridging():
    """Test MCPClient registering mock tools into ToolRegistry and calling them."""
    server_name = "test_analytics"
    tools_dict = {
        "calculate_growth": {
            "description": "Calculate quarter-over-quarter percentage growth",
            "parameters": {
                "type": "object",
                "properties": {
                    "current": {"type": "number"},
                    "previous": {"type": "number"},
                },
                "required": ["current", "previous"],
            },
            "handler": lambda current=0, previous=1: f"Growth: {((current - previous) / previous) * 100:.1f}%",
        }
    }

    client = mcp_hub.register_client(server_name, tools_dict=tools_dict)
    assert client.is_connected is True
    assert "calculate_growth" in client.list_remote_tools()

    # Verify tool was bridged into ToolRegistry
    bridged_tool_name = f"mcp_{server_name}_calculate_growth"
    tool = tool_registry.get(bridged_tool_name)
    assert tool is not None

    # Execute via ToolRegistry
    res = tool(current=150, previous=100)
    assert res.get("status") == "success"
    assert "50.0%" in res.get("result", "")

    # Execute directly via client
    client_res = client.call_tool("calculate_growth", {"current": 200, "previous": 100})
    assert client_res["status"] == "success"
    assert "100.0%" in client_res["result"]

    # Remove server and ensure bridged tool is cleaned up
    assert mcp_hub.remove_server(server_name) is True
    assert tool_registry.get(bridged_tool_name) is None


# ── 5. Autonomous AI Extension Tools Tests ────────────────────────────────────

def test_autonomous_ai_tools():
    """Test the AI self-extension tools (plugin_*, skill_*, mcp_*)."""
    # 1. Plugin List
    p_list_raw = tool_plugin_list(query="github")
    p_list = json.loads(p_list_raw)
    assert "marketplace_plugins" in p_list
    assert any(p["name"] == "github" for p in p_list["marketplace_plugins"])

    # 2. Skill Install from structured args
    s_install_raw = tool_skill_install(
        name="ai_synthesized_check",
        description="Autonomous verification step",
        tools="system_get_telemetry",
        tags="ai,test",
    )
    s_install = json.loads(s_install_raw)
    assert s_install["status"] == "success"

    # 3. Skill List
    s_list_raw = tool_skill_list(query="ai_synthesized_check")
    s_list = json.loads(s_list_raw)
    assert any(s["name"] == "ai_synthesized_check" for s in s_list)

    # 4. Skill Execute
    s_exec_raw = tool_skill_execute(skill_name="ai_synthesized_check")
    s_exec = json.loads(s_exec_raw)
    assert s_exec["success"] is True

    # 5. MCP List Servers
    mcp_list_raw = tool_mcp_list_servers()
    mcp_list = json.loads(mcp_list_raw)
    assert isinstance(mcp_list, list)

    # Cleanup skill
    skill_library.delete_skill("ai_synthesized_check")


# ── 6. Fast Intent Recognition Tests ──────────────────────────────────────────

def test_fast_intents_for_plugins_and_mcp():
    """Verify fast intent rule recognition for plugins and MCP commands."""
    intent_p_list = parse_fast_intent("plugin list")
    assert intent_p_list is not None
    assert intent_p_list.tool_name == "plugin_list"

    intent_p_install = parse_fast_intent("plugin install github")
    assert intent_p_install is not None
    assert intent_p_install.tool_name == "plugin_install"
    assert intent_p_install.parameters.get("source") == "github"

    intent_mcp_list = parse_fast_intent("mcp list")
    assert intent_mcp_list is not None
    assert intent_mcp_list.tool_name == "mcp_list_servers"

    intent_mcp_add = parse_fast_intent("mcp add sqlite npx -y @modelcontextprotocol/server-sqlite")
    assert intent_mcp_add is not None
    assert intent_mcp_add.tool_name == "mcp_add_server"
    assert intent_mcp_add.parameters.get("server_name") == "sqlite"

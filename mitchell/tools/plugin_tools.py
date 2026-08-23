"""Autonomous AI tools for managing Plugins, Claude Marketplaces, Skills, and MCP Servers."""

import json
from typing import Any, Dict, List, Optional

from mitchell.mcp_client.hub import mcp_hub
from mitchell.plugins.installer import plugin_installer
from mitchell.plugins.loader import plugin_loader
from mitchell.plugins.marketplace import plugin_marketplace
from mitchell.skills.executor import skill_executor
from mitchell.skills.library import skill_library
from mitchell.tools.registry import Tool


def tool_plugin_install(source: str, marketplace: Optional[str] = "claude-plugins-official") -> str:
    """Install a plugin from the official Claude marketplace (e.g. 'github', 'sqlite', 'fetch', 'memory', 'docker'), a Git repository URL, or a local directory."""
    res = plugin_installer.install(source=source, marketplace=marketplace)
    return json.dumps(res, indent=2)


def tool_plugin_list(query: str = "", include_marketplace: bool = True) -> str:
    """List all currently installed plugins and optionally search available marketplace catalog plugins."""
    installed = plugin_loader.list_plugins()
    result: Dict[str, Any] = {"installed_plugins": installed, "installed_count": len(installed)}

    if include_marketplace:
        available = plugin_marketplace.search_catalog(query=query)
        result["marketplace_plugins"] = [
            {
                "name": p.name,
                "version": p.version,
                "description": p.description,
                "marketplace": p.marketplace,
                "category": p.category,
                "has_mcp": p.has_mcp,
                "has_skills": p.has_skills,
                "installed": any(i["name"].lower() == p.name.lower() for i in installed),
            }
            for p in available
        ]
        result["marketplace_count"] = len(available)

    return json.dumps(result, indent=2)


def tool_plugin_uninstall(plugin_name: str) -> str:
    """Uninstall an active plugin and remove its bridged MCP servers and tools."""
    res = plugin_installer.uninstall(plugin_name=plugin_name)
    return json.dumps(res, indent=2)


def tool_skill_install(
    name: str,
    description: str,
    markdown_content: Optional[str] = None,
    tools: Optional[str] = None,
    tags: Optional[str] = None,
) -> str:
    """Install or synthesize a new procedural skill into the Skill Library from Markdown or structured parameters."""
    if markdown_content and markdown_content.strip():
        skill = skill_library.install_skill_markdown(markdown_content, name=name)
        return json.dumps({
            "status": "success",
            "message": f"Installed skill '{skill.name}' from markdown specification",
            "skill": skill.model_dump(mode="json"),
        }, indent=2)

    tool_list = [t.strip() for t in tools.split(",")] if tools else []
    tag_list = [t.strip() for t in tags.split(",")] if tags else ["custom"]

    from mitchell.skills.schema import Skill, SkillStep
    skill = Skill(
        name=name,
        description=description,
        tags=tag_list,
        source="organic",
        required_tools=tool_list,
        steps=[
            SkillStep(
                step_index=1,
                name=f"Execute {name}",
                action_type="tool" if tool_list else "agent",
                target=tool_list[0] if tool_list else "manager",
            )
        ],
    )
    saved = skill_library.save_skill(skill)
    return json.dumps({
        "status": "success",
        "message": f"Created and indexed procedural skill '{saved.name}'",
        "skill": saved.model_dump(mode="json"),
    }, indent=2)


def tool_skill_execute(skill_name: str, parameters_json: Optional[str] = None) -> str:
    """Execute a registered procedural skill step-by-step with given parameter values."""
    params: Dict[str, Any] = {}
    if parameters_json:
        try:
            params = json.loads(parameters_json)
        except Exception:
            params = {"raw": parameters_json}

    res = skill_executor.execute(skill_name, parameters=params)
    return json.dumps(res, indent=2)


def tool_skill_list(query: str = "") -> str:
    """List or semantically search procedural skills in the library."""
    if query:
        skills = skill_library.search_skills(query=query, top_k=10)
    else:
        skills = skill_library.list_skills()

    return json.dumps([
        {
            "name": s.name,
            "version": s.version,
            "description": s.description,
            "tags": s.tags,
            "source": s.source,
            "required_tools": s.required_tools,
            "confidence": s.confidence,
            "executions": s.stats.executions,
        }
        for s in skills
    ], indent=2)


def tool_mcp_add_server(
    server_name: str,
    command: str,
    args_json: Optional[str] = None,
    env_json: Optional[str] = None,
) -> str:
    """Add and launch a new stdio Model Context Protocol (MCP) server, automatically discovering and bridging its remote tools."""
    args: List[str] = []
    if args_json:
        try:
            parsed = json.loads(args_json)
            if isinstance(parsed, list):
                args = [str(a) for a in parsed]
        except Exception:
            args = args_json.split()

    env: Dict[str, str] = {}
    if env_json:
        try:
            parsed_env = json.loads(env_json)
            if isinstance(parsed_env, dict):
                env = {str(k): str(v) for k, v in parsed_env.items()}
        except Exception:
            pass

    client = mcp_hub.add_stdio_server(
        server_name=server_name,
        command=command,
        args=args,
        env=env,
        persist=True,
    )

    return json.dumps({
        "status": "connected" if client.is_connected else "failed",
        "server_name": server_name,
        "command": command,
        "tools_discovered": len(client.remote_tools),
        "tools": client.list_remote_tools(),
    }, indent=2)


def tool_mcp_remove_server(server_name: str) -> str:
    """Stop, unbridge tools, and remove a connected MCP server."""
    success = mcp_hub.remove_server(server_name)
    return json.dumps({
        "status": "success" if success else "not_found",
        "server_name": server_name,
    }, indent=2)


def tool_mcp_list_servers() -> str:
    """List all connected external MCP servers and their provided bridged tools."""
    servers = mcp_hub.list_servers()
    return json.dumps(servers, indent=2)


def tool_mcp_call_tool(server_name: str, tool_name: str, arguments_json: Optional[str] = None) -> str:
    """Directly execute a remote tool on a specific connected MCP server."""
    client = mcp_hub.get_client(server_name)
    if not client:
        return json.dumps({"error": f"MCP server '{server_name}' not found or not connected"})

    args: Dict[str, Any] = {}
    if arguments_json:
        try:
            args = json.loads(arguments_json)
        except Exception:
            args = {"input": arguments_json}

    res = client.call_tool(tool_name, arguments=args)
    return json.dumps(res, indent=2)


# Register Tool instances
plugin_install_tool = Tool(
    name="plugin_install",
    description="Install a plugin from the Claude official marketplace ('github', 'sqlite', 'fetch', 'memory', 'docker', 'python-lsp', 'typescript-lsp', etc.), GitHub repo URL, or local path.",
    parameters={
        "type": "object",
        "properties": {
            "source": {"type": "string", "description": "Plugin name (e.g. 'github', 'sqlite'), GitHub URL, or local directory path"},
            "marketplace": {"type": "string", "description": "Marketplace catalog name (default: 'claude-plugins-official')"},
        },
        "required": ["source"],
    },
    function=tool_plugin_install,
)

plugin_list_tool = Tool(
    name="plugin_list",
    description="List active installed plugins and browse available marketplace catalog plugins.",
    parameters={
        "type": "object",
        "properties": {
            "query": {"type": "string", "description": "Optional search term for plugins"},
            "include_marketplace": {"type": "boolean", "description": "Whether to include available marketplace catalog"},
        },
    },
    function=tool_plugin_list,
)

plugin_uninstall_tool = Tool(
    name="plugin_uninstall",
    description="Uninstall a plugin and unbridge its MCP servers and tools.",
    parameters={
        "type": "object",
        "properties": {
            "plugin_name": {"type": "string", "description": "Name of the plugin to remove"},
        },
        "required": ["plugin_name"],
    },
    function=tool_plugin_uninstall,
)

skill_install_tool = Tool(
    name="skill_install",
    description="Create, synthesize, or install a new procedural skill into the Skill Library.",
    parameters={
        "type": "object",
        "properties": {
            "name": {"type": "string", "description": "Unique identifier name for the skill"},
            "description": {"type": "string", "description": "Detailed description of the skill procedure"},
            "markdown_content": {"type": "string", "description": "Optional full SKILL.md markdown text with YAML frontmatter"},
            "tools": {"type": "string", "description": "Comma-separated list of required tool names"},
            "tags": {"type": "string", "description": "Comma-separated categorization tags"},
        },
        "required": ["name", "description"],
    },
    function=tool_skill_install,
)

skill_execute_tool = Tool(
    name="skill_execute",
    description="Execute a registered procedural skill by name.",
    parameters={
        "type": "object",
        "properties": {
            "skill_name": {"type": "string", "description": "Name of the skill to run"},
            "parameters_json": {"type": "string", "description": "JSON object string of input parameters"},
        },
        "required": ["skill_name"],
    },
    function=tool_skill_execute,
)

skill_list_tool = Tool(
    name="skill_list",
    description="List or semantically search procedural skills in the library.",
    parameters={
        "type": "object",
        "properties": {
            "query": {"type": "string", "description": "Search query or leave empty to list all"},
        },
    },
    function=tool_skill_list,
)

mcp_add_server_tool = Tool(
    name="mcp_add_server",
    description="Add and connect an external Model Context Protocol (MCP) server via stdio JSON-RPC subprocess command.",
    parameters={
        "type": "object",
        "properties": {
            "server_name": {"type": "string", "description": "Unique identifier name for the MCP server"},
            "command": {"type": "string", "description": "Subprocess command binary (e.g. 'npx', 'uvx', 'python')"},
            "args_json": {"type": "string", "description": "JSON list or space-separated command arguments"},
            "env_json": {"type": "string", "description": "JSON dictionary of environment variables"},
        },
        "required": ["server_name", "command"],
    },
    function=tool_mcp_add_server,
)

mcp_remove_server_tool = Tool(
    name="mcp_remove_server",
    description="Disconnect and remove an external MCP server.",
    parameters={
        "type": "object",
        "properties": {
            "server_name": {"type": "string", "description": "Name of the MCP server to disconnect"},
        },
        "required": ["server_name"],
    },
    function=tool_mcp_remove_server,
)

mcp_list_servers_tool = Tool(
    name="mcp_list_servers",
    description="List all active external MCP servers and bridged remote tools.",
    parameters={"type": "object", "properties": {}},
    function=tool_mcp_list_servers,
)

mcp_call_tool_tool = Tool(
    name="mcp_call_tool",
    description="Directly execute a remote tool on a connected MCP server.",
    parameters={
        "type": "object",
        "properties": {
            "server_name": {"type": "string", "description": "MCP server name"},
            "tool_name": {"type": "string", "description": "Tool name on the MCP server"},
            "arguments_json": {"type": "string", "description": "JSON object string of tool arguments"},
        },
        "required": ["server_name", "tool_name"],
    },
    function=tool_mcp_call_tool,
)

TOOLS = [
    plugin_install_tool,
    plugin_list_tool,
    plugin_uninstall_tool,
    skill_install_tool,
    skill_execute_tool,
    skill_list_tool,
    mcp_add_server_tool,
    mcp_remove_server_tool,
    mcp_list_servers_tool,
    mcp_call_tool_tool,
]

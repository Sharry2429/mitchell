"""Mesh, MCP Client Hub, and Plugin management tools for Mitchell ToolRegistry."""

import json
from typing import Any, Dict, Optional

from mitchell.mcp_client.hub import mcp_hub
from mitchell.mesh.coordinator import mesh_coordinator
from mitchell.mesh.protocol import MeshTaskRequest
from mitchell.plugins.loader import plugin_loader
from mitchell.tools.registry import Tool


def tool_mesh_list_nodes() -> str:
    """List all connected physical nodes in the distributed agent mesh cluster."""
    nodes = mesh_coordinator.list_nodes()
    return json.dumps(nodes, indent=2)


def tool_mesh_dispatch(goal: str, required_capability: Optional[str] = None) -> str:
    """Dispatch an autonomous goal to the optimal physical node in the mesh cluster."""
    req = MeshTaskRequest(goal=goal, required_capability=required_capability)
    res = mesh_coordinator.dispatch_task(req)
    return json.dumps(res.model_dump(), indent=2)


def tool_mcp_list_servers() -> str:
    """List all external connected MCP servers and their available tools."""
    servers = mcp_hub.list_servers()
    return json.dumps(servers, indent=2)


def tool_plugin_list() -> str:
    """List all active drop-in plugins loaded from .mitchell/plugins."""
    plugins = plugin_loader.list_plugins()
    return json.dumps(plugins, indent=2)


mesh_nodes_tool = Tool(
    name="mesh_list_nodes",
    description="List active nodes, operating systems, and advertised capabilities in the mesh cluster.",
    parameters={"type": "object", "properties": {}},
    function=tool_mesh_list_nodes,
)

mesh_dispatch_tool = Tool(
    name="mesh_dispatch_remote",
    description="Dispatch a subtask across the distributed mesh cluster to a remote node.",
    parameters={
        "type": "object",
        "properties": {
            "goal": {"type": "string", "description": "Subtask goal to execute remotely"},
            "required_capability": {"type": "string", "description": "Required capability (e.g. 'windows_uia', 'browser', 'gpu')"},
        },
        "required": ["goal"],
    },
    function=tool_mesh_dispatch,
)

mcp_servers_tool = Tool(
    name="mcp_list_external_servers",
    description="List connected external MCP servers and bridged remote tools.",
    parameters={"type": "object", "properties": {}},
    function=tool_mcp_list_servers,
)

plugin_list_tool = Tool(
    name="plugin_list_active",
    description="List all active loaded plugins in the Mitchell system.",
    parameters={"type": "object", "properties": {}},
    function=tool_plugin_list,
)

TOOLS = [mesh_nodes_tool, mesh_dispatch_tool, mcp_servers_tool, plugin_list_tool]

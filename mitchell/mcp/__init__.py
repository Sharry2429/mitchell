"""Mitchell Model Context Protocol (MCP) Server & Client Package.

Unified Model Context Protocol layer exposing all Mitchell tools, resources,
and prompts to external AI IDEs (Claude Code, Cursor, Antigravity, VS Code)
and internally to Mitchell AI Core.
"""

from mitchell.mcp.client import MitchellMCPClient, mcp_client
from mitchell.mcp.prompts import MCPPromptManager, mcp_prompt_manager
from mitchell.mcp.protocol import (
    JSONRPCRequest,
    JSONRPCResponse,
    MCPPrompt,
    MCPResource,
    MCPResourceContent,
    MCPTextContent,
    MCPTool,
    MCPToolResult,
)
from mitchell.mcp.resources import MCPResourceManager, mcp_resource_manager
from mitchell.mcp.server import MitchellMCPServer, mcp_server
from mitchell.mcp.tools_adapter import MCPToolAdapter, mcp_tool_adapter

__all__ = [
    "MitchellMCPServer",
    "mcp_server",
    "MitchellMCPClient",
    "mcp_client",
    "MCPToolAdapter",
    "mcp_tool_adapter",
    "MCPResourceManager",
    "mcp_resource_manager",
    "MCPPromptManager",
    "mcp_prompt_manager",
    "MCPTool",
    "MCPToolResult",
    "MCPTextContent",
    "MCPResource",
    "MCPResourceContent",
    "MCPPrompt",
    "JSONRPCRequest",
    "JSONRPCResponse",
]

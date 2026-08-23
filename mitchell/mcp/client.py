"""Mitchell MCP Client for accessing Mitchell MCP Server and external MCP servers."""

import asyncio
import json
import subprocess
import threading
from typing import Any, Dict, List, Optional

from mitchell.core.event_log import event_log
from mitchell.core.logging import logger
from mitchell.mcp.protocol import MCPTool
from mitchell.mcp.server import MitchellMCPServer, mcp_server


class MitchellMCPClient:
    """Universal MCP Client allowing Mitchell AI to access all tools and resources over MCP."""

    def __init__(self, in_process_server: Optional[MitchellMCPServer] = None) -> None:
        self.in_process_server = in_process_server or mcp_server
        self._cached_tools: Dict[str, MCPTool] = {}
        self._initialized = False

    async def initialize(self) -> Dict[str, Any]:
        """Perform MCP initialize handshake."""
        req = {
            "jsonrpc": "2.0",
            "id": "init-1",
            "method": "initialize",
            "params": {
                "protocolVersion": "2024-11-05",
                "capabilities": {"roots": {"listChanged": True}},
                "clientInfo": {"name": "mitchell-ai-core", "version": "1.0.0"},
            },
        }
        res = await self.in_process_server.handle_request(req)
        self._initialized = True
        return res or {}

    async def list_tools(self) -> List[MCPTool]:
        """Retrieve all available MCP tools."""
        if not self._initialized:
            await self.initialize()

        req = {
            "jsonrpc": "2.0",
            "id": "tools-list-1",
            "method": "tools/list",
            "params": {},
        }
        res = await self.in_process_server.handle_request(req)
        tools_data = (res or {}).get("result", {}).get("tools", [])
        tools = [MCPTool(**t) for t in tools_data]
        self._cached_tools = {t.name: t for t in tools}
        return tools

    async def call_tool(self, name: str, arguments: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Invoke an MCP tool by name with arguments."""
        if not self._initialized:
            await self.initialize()

        req = {
            "jsonrpc": "2.0",
            "id": f"call-{name}",
            "method": "tools/call",
            "params": {
                "name": name,
                "arguments": arguments or {},
            },
        }
        res = await self.in_process_server.handle_request(req)
        result = (res or {}).get("result", {})
        event_log.log_event("mcp_client_tool_called", source="mcp_client", data={"tool": name, "result": result})
        return result

    async def list_resources(self) -> List[Dict[str, Any]]:
        """List available MCP resources."""
        req = {
            "jsonrpc": "2.0",
            "id": "res-list-1",
            "method": "resources/list",
            "params": {},
        }
        res = await self.in_process_server.handle_request(req)
        return (res or {}).get("result", {}).get("resources", [])

    async def read_resource(self, uri: str) -> Optional[str]:
        """Read resource content by URI."""
        req = {
            "jsonrpc": "2.0",
            "id": f"res-read-{uri}",
            "method": "resources/read",
            "params": {"uri": uri},
        }
        res = await self.in_process_server.handle_request(req)
        contents = (res or {}).get("result", {}).get("contents", [])
        if contents:
            return contents[0].get("text")
        return None

    def get_openai_tool_definitions(self) -> List[Dict[str, Any]]:
        """Convert MCP tools into OpenAI function calling format."""
        openai_tools = []
        for name, tool in self._cached_tools.items():
            openai_tools.append({
                "type": "function",
                "function": {
                    "name": tool.name,
                    "description": tool.description,
                    "parameters": tool.inputSchema,
                },
            })
        return openai_tools


mcp_client = MitchellMCPClient()

__all__ = ["MitchellMCPClient", "mcp_client"]

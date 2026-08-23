"""Model Context Protocol (MCP) Server for Mitchell AI.

Implements official MCP Specification (2024-11-05) exposing:
- All Tools (System, IDE, Browser, Desktop UIA, Android, IoT, Documents, Research, Harness, Teaching, Takeover)
- Resources (System telemetry, workspace tree, blackboard, self-model, documents)
- Prompts (Karpathy engineering principles, autonomous takeover, deep research)
"""

import asyncio
import json
import sys
from typing import Any, Dict, Optional

from mitchell.core.event_log import event_log
from mitchell.core.logging import logger
from mitchell.mcp.prompts import mcp_prompt_manager
from mitchell.mcp.protocol import (
    INTERNAL_ERROR,
    INVALID_PARAMS,
    INVALID_REQUEST,
    METHOD_NOT_FOUND,
)
from mitchell.mcp.resources import mcp_resource_manager
from mitchell.mcp.tools_adapter import mcp_tool_adapter


class MitchellMCPServer:
    """Standard MCP JSON-RPC Server for Mitchell Multi-Pillar Tools & Resources."""

    def __init__(self) -> None:
        self.tool_adapter = mcp_tool_adapter
        self.resource_manager = mcp_resource_manager
        self.prompt_manager = mcp_prompt_manager
        self.server_info = {
            "name": "mitchell-mcp",
            "version": "1.0.0",
        }


    async def run_stdio(self) -> None:
        """Run JSON-RPC loop reading from stdin and writing to stdout."""
        loop = asyncio.get_running_loop()
        reader = asyncio.StreamReader()
        protocol = asyncio.StreamReaderProtocol(reader)
        await loop.connect_read_pipe(lambda: protocol, sys.stdin)

        logger.info("Mitchell MCP Server running on stdio...")

        while True:
            line = await reader.readline()
            if not line:
                break

            line_str = line.decode("utf-8").strip()
            if not line_str:
                continue

            try:
                request = json.loads(line_str)
                response = await self.handle_request(request)
                if response is not None:
                    out = json.dumps(response) + "\n"
                    sys.stdout.write(out)
                    sys.stdout.flush()
            except Exception as exc:
                logger.error("MCP stdio loop error: {}", exc)

    async def handle_request(self, req: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Process incoming JSON-RPC 2.0 request or notification."""
        msg_id = req.get("id")
        method = req.get("method", "")
        params = req.get("params", {})

        # Handle notifications (no id)
        if msg_id is None:
            if method == "notifications/initialized":
                logger.info("MCP Client connection initialized.")
            return None

        # 1. Initialize
        if method == "initialize":
            return {
                "jsonrpc": "2.0",
                "id": msg_id,
                "result": {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {
                        "tools": {"listChanged": True},
                        "resources": {"listChanged": True, "subscribe": False},
                        "prompts": {"listChanged": False},
                    },
                    "serverInfo": self.server_info,
                },
            }

        # 2. Ping
        if method == "ping":
            return {"jsonrpc": "2.0", "id": msg_id, "result": {}}

        # 3. Tools List
        if method == "tools/list":
            tools = self.tool_adapter.list_mcp_tools()
            return {
                "jsonrpc": "2.0",
                "id": msg_id,
                "result": {"tools": [t.model_dump() for t in tools]},
            }

        # 4. Tools Call
        if method == "tools/call":
            name = params.get("name", "")
            arguments = params.get("arguments", {})
            result = self.tool_adapter.execute_tool(name=name, arguments=arguments)
            return {
                "jsonrpc": "2.0",
                "id": msg_id,
                "result": result.model_dump(),
            }

        # 5. Resources List
        if method == "resources/list":
            resources = self.resource_manager.list_resources()
            return {
                "jsonrpc": "2.0",
                "id": msg_id,
                "result": {"resources": [r.model_dump() for r in resources]},
            }

        # 6. Resources Read
        if method == "resources/read":
            uri = params.get("uri", "")
            content = self.resource_manager.read_resource(uri=uri)
            if content:
                return {
                    "jsonrpc": "2.0",
                    "id": msg_id,
                    "result": {"contents": [content.model_dump()]},
                }
            return {
                "jsonrpc": "2.0",
                "id": msg_id,
                "error": {"code": INVALID_PARAMS, "message": f"Resource with URI '{uri}' not found"},
            }

        # 7. Prompts List
        if method == "prompts/list":
            prompts = self.prompt_manager.list_prompts()
            return {
                "jsonrpc": "2.0",
                "id": msg_id,
                "result": {"prompts": [p.model_dump() for p in prompts]},
            }

        # 8. Prompts Get
        if method == "prompts/get":
            name = params.get("name", "")
            arguments = params.get("arguments", {})
            prompt_data = self.prompt_manager.get_prompt(name=name, arguments=arguments)
            if prompt_data:
                return {
                    "jsonrpc": "2.0",
                    "id": msg_id,
                    "result": prompt_data,
                }
            return {
                "jsonrpc": "2.0",
                "id": msg_id,
                "error": {"code": INVALID_PARAMS, "message": f"Prompt '{name}' not found"},
            }

        # Method not found
        return {
            "jsonrpc": "2.0",
            "id": msg_id,
            "error": {"code": METHOD_NOT_FOUND, "message": f"Method '{method}' not recognized"},
        }


mcp_server = MitchellMCPServer()

__all__ = ["MitchellMCPServer", "mcp_server"]

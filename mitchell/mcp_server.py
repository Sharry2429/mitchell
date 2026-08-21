"""Model Context Protocol (MCP) stdio server for Mitchell multi-pillar tools and skills."""

import asyncio
import json
import sys
from typing import Any, Dict, List, Optional

from mitchell.core.event_log import event_log
from mitchell.core.llm import KARPATHY_SYSTEM_PROMPT
from mitchell.core.logging import logger
from mitchell.tools.registry import tool_registry


class MitchellMCPServer:
    """Standard MCP JSON-RPC stdio server exposing Mitchell tools to external AI clients."""

    def __init__(self) -> None:
        self.tool_reg = tool_registry
        self.tool_reg.discover()
        self.server_info = {
            "name": "mitchell-mcp",
            "version": "0.1.0",
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
                logger.error("MCP RPC error: {}", exc)

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
                        "tools": {"listChanged": False},
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
            tools_list = []
            for t in self.tool_reg.list_tools():
                tool_obj = self.tool_reg.get(t["name"])
                schema = tool_obj.parameters if tool_obj else {"type": "object", "properties": {}}
                tools_list.append({
                    "name": t["name"],
                    "description": t["description"],
                    "inputSchema": schema,
                })
            return {
                "jsonrpc": "2.0",
                "id": msg_id,
                "result": {"tools": tools_list},
            }

        # 4. Tools Call
        if method == "tools/call":
            name = params.get("name", "")
            arguments = params.get("arguments", {})
            tool = self.tool_reg.get(name)

            if not tool:
                return {
                    "jsonrpc": "2.0",
                    "id": msg_id,
                    "error": {"code": -32601, "message": f"Tool '{name}' not found"},
                }

            try:
                logger.info("MCP invoking tool '{}' with args: {}", name, arguments)
                result = tool(**arguments)
                event_log.log_event("mcp_tool_called", source="mcp_server", data={"tool": name, "arguments": arguments})
                return {
                    "jsonrpc": "2.0",
                    "id": msg_id,
                    "result": {
                        "content": [
                            {"type": "text", "text": str(result)}
                        ],
                        "isError": False,
                    },
                }
            except Exception as exc:
                logger.error("Error running MCP tool '{}': {}", name, exc)
                return {
                    "jsonrpc": "2.0",
                    "id": msg_id,
                    "result": {
                        "content": [
                            {"type": "text", "text": f"Error: {exc}"}
                        ],
                        "isError": True,
                    },
                }

        # 5. Prompts List
        if method == "prompts/list":
            return {
                "jsonrpc": "2.0",
                "id": msg_id,
                "result": {
                    "prompts": [
                        {
                            "name": "karpathy_principles",
                            "description": "Mitchell's core engineering principles (Think Before Acting, Simplicity First, Surgical Changes, Goal-Driven)",
                        }
                    ]
                },
            }

        # 6. Prompts Get
        if method == "prompts/get":
            prompt_name = params.get("name")
            if prompt_name == "karpathy_principles":
                return {
                    "jsonrpc": "2.0",
                    "id": msg_id,
                    "result": {
                        "description": "Mitchell Karpathy Principles System Prompt",
                        "messages": [
                            {"role": "system", "content": {"type": "text", "text": KARPATHY_SYSTEM_PROMPT}}
                        ],
                    },
                }
            return {
                "jsonrpc": "2.0",
                "id": msg_id,
                "error": {"code": -32602, "message": f"Prompt '{prompt_name}' not found"},
            }

        # Method not found
        return {
            "jsonrpc": "2.0",
            "id": msg_id,
            "error": {"code": -32601, "message": f"Method '{method}' not recognized"},
        }


def main() -> None:
    """Entry point for mitchell-mcp console script."""
    server = MitchellMCPServer()
    try:
        asyncio.run(server.run_stdio())
    except (KeyboardInterrupt, EOFError):
        pass


if __name__ == "__main__":
    main()

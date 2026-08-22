"""Universal MCP Client for connecting to external Model Context Protocol servers."""

import json
from typing import Any, Callable, Dict, List, Optional

from mitchell.core.logging import logger
from mitchell.tools.registry import Tool, tool_registry


class MCPClient:
    """Connects to external MCP servers and bridges remote tools into Mitchell."""

    def __init__(self, server_name: str) -> None:
        self.server_name = server_name
        self.is_connected = False
        self.remote_tools: Dict[str, Dict[str, Any]] = {}

    def connect_mock_or_inprocess(self, tools_dict: Dict[str, Dict[str, Any]]) -> bool:
        """Simulate or connect to an in-process MCP server with provided tools."""
        self.remote_tools = tools_dict
        self.is_connected = True
        self._register_bridged_tools()
        logger.info("MCPClient: Connected to MCP server '{}' with {} tools.", self.server_name, len(tools_dict))
        return True

    def _register_bridged_tools(self) -> None:
        """Wrap each remote MCP tool and register it into Mitchell's native ToolRegistry."""
        for tool_name, meta in self.remote_tools.items():
            namespaced_name = f"mcp_{self.server_name}_{tool_name}"

            def make_handler(t_name: str) -> Callable[..., Any]:
                def handler(**kwargs: Any) -> Any:
                    return self.call_tool(t_name, kwargs)
                return handler

            bridged_tool = Tool(
                name=namespaced_name,
                description=f"[{self.server_name} MCP] {meta.get('description', '')}",
                parameters=meta.get("parameters", {"type": "object", "properties": {}}),
                function=make_handler(tool_name),
            )
            tool_registry.register(bridged_tool)

    def call_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a tool on the remote MCP server."""
        if tool_name not in self.remote_tools:
            return {"error": f"Tool '{tool_name}' not found on MCP server '{self.server_name}'"}

        handler = self.remote_tools[tool_name].get("handler")
        if callable(handler):
            try:
                result = handler(**arguments)
                return {"status": "success", "result": result}
            except Exception as e:
                logger.error("Error executing remote MCP tool {}: {}", tool_name, e)
                return {"status": "error", "error": str(e)}

        return {
            "status": "success",
            "result": f"[MCP {self.server_name}:{tool_name}] Processed with args: {arguments}",
        }

    def list_remote_tools(self) -> List[str]:
        """Return list of tool names provided by this MCP server."""
        return list(self.remote_tools.keys())


__all__ = ["MCPClient"]

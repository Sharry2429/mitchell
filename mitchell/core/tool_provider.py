"""
mitchell.core.tool_provider
============================
Tool-provider abstraction for the executor.

The core (Phase 2) must NOT depend on the live MCP server object (Phase 8 tool
surface). Instead the executor talks to a `ToolProvider` interface. The FastMCP
server is one implementation; in-process/static providers (used in tests) and a
future subprocess OpenCode provider are others. Swapping the backend never
requires rewriting the executor.

The MCP server is imported lazily inside the implementation, so importing the
core never pulls in fastmcp unless an MCP provider is actually constructed.
"""
from __future__ import annotations

from typing import Any, Callable, Dict, Optional


class ToolProvider:
    """Interface the executor uses to discover and call agent tools."""

    async def list_tools_openai(self) -> list[dict]:
        """Return tools in the OpenAI function-calling schema."""
        raise NotImplementedError

    async def call_tool(self, name: str, arguments: dict[str, Any]) -> str:
        """Invoke a tool by name; return its textual result (or error string)."""
        raise NotImplementedError


class StaticToolProvider(ToolProvider):
    """In-process provider backed by plain callables. Used by tests and demos.

    No MCP server, no fastmcp, no subprocess — fully deterministic.
    """

    def __init__(self, tools: Optional[Dict[str, Callable]] = None) -> None:
        self.tools: Dict[str, Callable] = tools or {}

    def register(self, name: str, fn: Callable) -> None:
        self.tools[name] = fn

    async def list_tools_openai(self) -> list[dict]:
        return [
            {
                "type": "function",
                "function": {
                    "name": name,
                    "description": "",
                    "parameters": {"type": "object", "properties": {}},
                },
            }
            for name in self.tools
        ]

    async def call_tool(self, name: str, arguments: dict[str, Any]) -> str:
        if name not in self.tools:
            return f"Error executing tool: unknown tool '{name}'"
        try:
            return str(self.tools[name](**arguments))
        except Exception as e:  # noqa: BLE001 - surface any tool error to the agent
            return f"Error executing tool: {e}"


class MCPToolProvider(ToolProvider):
    """Wraps the live FastMCP server as a ToolProvider.

    The server module is imported lazily so the core never depends on its
    import-time side effects. This is the default used in production; it is
    swappable for a subprocess/OpenCode provider in Phase 6 without touching
    the executor.
    """

    async def list_tools_openai(self) -> list[dict]:
        from mitchell.mcp_server import mcp

        tools = await mcp.list_tools()
        return [
            {
                "type": "function",
                "function": {
                    "name": t.name,
                    "description": t.description or "",
                    "parameters": t.parameters or {},
                },
            }
            for t in tools
        ]

    async def call_tool(self, name: str, arguments: dict[str, Any]) -> str:
        from mitchell.mcp_server import mcp

        try:
            resp = await mcp.call_tool(name, arguments=arguments)
            texts = [c.text for c in resp if hasattr(c, "text")]
            return "\n".join(texts) if texts else str(resp)
        except Exception as e:  # noqa: BLE001
            return f"Error executing tool: {e}"

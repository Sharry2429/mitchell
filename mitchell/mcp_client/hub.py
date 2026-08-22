"""Universal MCP Client Hub managing connections to multiple external MCP servers."""

from typing import Any, Dict, List, Optional

from mitchell.core.logging import logger
from mitchell.mcp_client.client import MCPClient


class MCPClientHub:
    """Orchestrates connections to multiple external MCP servers."""

    def __init__(self) -> None:
        self.clients: Dict[str, MCPClient] = {}

    def register_client(self, server_name: str, tools_dict: Dict[str, Dict[str, Any]]) -> MCPClient:
        """Connect and register an external MCP server."""
        client = MCPClient(server_name=server_name)
        client.connect_mock_or_inprocess(tools_dict=tools_dict)
        self.clients[server_name] = client
        return client

    def get_client(self, server_name: str) -> Optional[MCPClient]:
        """Get connected MCP client by server name."""
        return self.clients.get(server_name)

    def list_servers(self) -> List[Dict[str, Any]]:
        """List all connected MCP servers and their provided tools."""
        result = []
        for name, client in self.clients.items():
            result.append({
                "server_name": name,
                "is_connected": client.is_connected,
                "tool_count": len(client.remote_tools),
                "tools": client.list_remote_tools(),
            })
        return result


mcp_hub = MCPClientHub()

__all__ = ["MCPClientHub", "mcp_hub"]

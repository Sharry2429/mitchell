"""Universal MCP Client Hub managing connections to multiple external MCP servers."""

import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from mitchell.core.event_log import event_log
from mitchell.core.logging import logger
from mitchell.mcp_client.client import MCPClient


class MCPClientHub:
    """Orchestrates connections to multiple external stdio and in-process MCP servers."""

    def __init__(self, config_path: Optional[Path] = None) -> None:
        self.root_dir = Path(__file__).resolve().parent.parent.parent
        self.config_path = config_path or (self.root_dir / ".mitchell" / "mcp_servers.json")
        self.clients: Dict[str, MCPClient] = {}
        self.server_configs: Dict[str, Dict[str, Any]] = {}
        self._load_saved_configs()

    def _load_saved_configs(self) -> None:
        """Load persistent MCP server configurations from disk."""
        if self.config_path.exists():
            try:
                data = json.loads(self.config_path.read_text(encoding="utf-8"))
                if isinstance(data, dict):
                    self.server_configs = data.get("mcpServers", data)
            except Exception as e:
                logger.error("Failed to parse MCP server config at {}: {}", self.config_path, e)

    def _save_configs(self) -> None:
        """Persist registered MCP server configurations to disk."""
        try:
            self.config_path.parent.mkdir(parents=True, exist_ok=True)
            self.config_path.write_text(
                json.dumps({"mcpServers": self.server_configs}, indent=2),
                encoding="utf-8",
            )
        except Exception as e:
            logger.error("Failed to save MCP config: {}", e)

    def add_stdio_server(
        self,
        server_name: str,
        command: str,
        args: Optional[List[str]] = None,
        env: Optional[Dict[str, str]] = None,
        persist: bool = True,
    ) -> MCPClient:
        """Launch and register a stdio MCP server subprocess."""
        if server_name in self.clients:
            self.remove_server(server_name)

        client = MCPClient(
            server_name=server_name,
            command=command,
            args=args or [],
            env=env or {},
        )
        client.start_stdio_server()
        self.clients[server_name] = client

        self.server_configs[server_name] = {
            "command": command,
            "args": args or [],
            "env": env or {},
            "type": "stdio",
        }
        if persist:
            self._save_configs()

        event_log.log_event(
            "mcp_server_added",
            source="mcp_hub",
            data={"server_name": server_name, "command": command},
        )
        return client

    def register_client(self, server_name: str, tools_dict: Dict[str, Dict[str, Any]]) -> MCPClient:
        """Connect and register an in-process MCP server with pre-defined tools."""
        if server_name in self.clients:
            self.remove_server(server_name)

        client = MCPClient(server_name=server_name)
        client.connect_mock_or_inprocess(tools_dict=tools_dict)
        self.clients[server_name] = client
        return client

    def remove_server(self, server_name: str) -> bool:
        """Stop, unregister tools, and remove an MCP server."""
        client = self.clients.pop(server_name, None)
        if client:
            client.stop()
            self.server_configs.pop(server_name, None)
            self._save_configs()
            event_log.log_event(
                "mcp_server_removed",
                source="mcp_hub",
                data={"server_name": server_name},
            )
            return True
        return False

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

    def load_from_manifest(self, mcp_dict: Dict[str, Any]) -> List[MCPClient]:
        """Load MCP servers declared inside a plugin or workspace manifest."""
        added = []
        servers = mcp_dict.get("mcpServers", mcp_dict)
        for s_name, s_cfg in servers.items():
            if isinstance(s_cfg, dict):
                cmd = s_cfg.get("command")
                if cmd:
                    cl = self.add_stdio_server(
                        server_name=s_name,
                        command=cmd,
                        args=s_cfg.get("args", []),
                        env=s_cfg.get("env", {}),
                        persist=False,
                    )
                    added.append(cl)
        return added


mcp_hub = MCPClientHub()

__all__ = ["MCPClientHub", "mcp_hub"]

"""Universal MCP Client for connecting to external Model Context Protocol servers via stdio JSON-RPC or in-process."""

import json
import subprocess
import threading
import uuid
from typing import Any, Callable, Dict, List, Optional

from mitchell.core.logging import logger
from mitchell.tools.registry import Tool, tool_registry


class MCPClient:
    """Connects to external MCP servers via stdio JSON-RPC 2.0 subprocess or in-process bridge."""

    def __init__(
        self,
        server_name: str,
        command: Optional[str] = None,
        args: Optional[List[str]] = None,
        env: Optional[Dict[str, str]] = None,
    ) -> None:
        self.server_name = server_name
        self.command = command
        self.args = args or []
        self.env = env or {}
        self.is_connected = False
        self.remote_tools: Dict[str, Dict[str, Any]] = {}
        self.registered_tool_names: List[str] = []
        self.process: Optional[subprocess.Popen] = None
        self._lock = threading.Lock()

    def start_stdio_server(self) -> bool:
        """Launch stdio MCP subprocess and initialize connection."""
        if not self.command:
            logger.error("Cannot start stdio server '{}': No command provided", self.server_name)
            return False

        full_cmd = [self.command] + self.args
        try:
            import os
            proc_env = os.environ.copy()
            proc_env.update(self.env)

            self.process = subprocess.Popen(
                full_cmd,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=1,
                env=proc_env,
            )

            # Perform MCP initialize handshake
            init_res = self._send_json_rpc(
                method="initialize",
                params={
                    "protocolVersion": "2024-11-05",
                    "capabilities": {"roots": {"listChanged": True}, "sampling": {}},
                    "clientInfo": {"name": "mitchell-mcp-client", "version": "1.0.0"},
                },
            )
            if not init_res or "error" in init_res:
                logger.warning("MCP Initialize response for '{}': {}", self.server_name, init_res)

            # Send initialized notification
            self._send_notification(method="notifications/initialized")

            # Fetch remote tools
            tools_res = self._send_json_rpc(method="tools/list", params={})
            tools_list = []
            if tools_res and "result" in tools_res and "tools" in tools_res["result"]:
                tools_list = tools_res["result"]["tools"]

            self.remote_tools = {}
            for t in tools_list:
                t_name = t.get("name", "")
                if t_name:
                    self.remote_tools[t_name] = {
                        "description": t.get("description", ""),
                        "parameters": t.get("inputSchema", {"type": "object", "properties": {}}),
                    }

            self.is_connected = True
            self._register_bridged_tools()
            logger.info(
                "MCPClient: Successfully connected to stdio server '{}' ({} tools discovered)",
                self.server_name,
                len(self.remote_tools),
            )
            return True
        except Exception as e:
            logger.error("Failed to start MCP stdio server '{}': {}", self.server_name, e)
            self.stop()
            return False

    def connect_mock_or_inprocess(self, tools_dict: Dict[str, Dict[str, Any]]) -> bool:
        """Simulate or connect to an in-process MCP server with provided tools."""
        self.remote_tools = tools_dict
        self.is_connected = True
        self._register_bridged_tools()
        logger.info("MCPClient: Connected to in-process MCP server '{}' with {} tools.", self.server_name, len(tools_dict))
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
            self.registered_tool_names.append(namespaced_name)

    def _send_json_rpc(self, method: str, params: Optional[Dict[str, Any]] = None) -> Optional[Dict[str, Any]]:
        """Send a JSON-RPC 2.0 request over stdio and await response line."""
        if not self.process or not self.process.stdin or not self.process.stdout:
            return None

        req_id = str(uuid.uuid4())
        msg = {
            "jsonrpc": "2.0",
            "id": req_id,
            "method": method,
            "params": params or {},
        }

        with self._lock:
            try:
                line_to_send = json.dumps(msg) + "\n"
                self.process.stdin.write(line_to_send)
                self.process.stdin.flush()

                # Read response line
                resp_line = self.process.stdout.readline()
                if not resp_line:
                    return None
                return json.loads(resp_line.strip())
            except Exception as e:
                logger.error("JSON-RPC communication error on '{}': {}", self.server_name, e)
                return None

    def _send_notification(self, method: str, params: Optional[Dict[str, Any]] = None) -> None:
        """Send a JSON-RPC 2.0 notification without expecting a response."""
        if not self.process or not self.process.stdin:
            return
        msg = {"jsonrpc": "2.0", "method": method, "params": params or {}}
        with self._lock:
            try:
                self.process.stdin.write(json.dumps(msg) + "\n")
                self.process.stdin.flush()
            except Exception:
                pass

    def call_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a tool on the MCP server (stdio or in-process)."""
        if tool_name not in self.remote_tools:
            return {"error": f"Tool '{tool_name}' not found on MCP server '{self.server_name}'"}

        # In-process handler check
        handler = self.remote_tools[tool_name].get("handler")
        if callable(handler):
            try:
                result = handler(**arguments)
                return {"status": "success", "result": result}
            except Exception as e:
                logger.error("Error executing in-process MCP tool {}: {}", tool_name, e)
                return {"status": "error", "error": str(e)}

        # Subprocess stdio dispatch
        if self.process:
            res = self._send_json_rpc(
                method="tools/call",
                params={"name": tool_name, "arguments": arguments},
            )
            if res and "result" in res:
                content = res["result"].get("content", [])
                if isinstance(content, list) and content and "text" in content[0]:
                    return {"status": "success", "result": content[0]["text"]}
                return {"status": "success", "result": res["result"]}
            elif res and "error" in res:
                return {"status": "error", "error": res["error"]}

        return {
            "status": "success",
            "result": f"[MCP {self.server_name}:{tool_name}] Processed with args: {arguments}",
        }

    def list_remote_tools(self) -> List[str]:
        """Return list of tool names provided by this MCP server."""
        return list(self.remote_tools.keys())

    def stop(self) -> None:
        """Terminate subprocess and unregister bridged tools."""
        self.is_connected = False
        if self.process:
            try:
                self.process.terminate()
                self.process.wait(timeout=2.0)
            except Exception:
                try:
                    self.process.kill()
                except Exception:
                    pass
            self.process = None

        # Unregister tools from ToolRegistry
        for t_name in self.registered_tool_names:
            tool_registry.unregister(t_name)
        self.registered_tool_names.clear()
        logger.info("MCP server '{}' stopped and unbridged.", self.server_name)


__all__ = ["MCPClient"]

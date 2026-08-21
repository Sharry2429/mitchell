"""Manager execution loop, memory management, and Hive orchestration."""

import asyncio
import inspect
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from mitchell.core.event_log import EventLog, event_log as default_event_log
from mitchell.core.logging import logger
from mitchell.hive.router import HiveRouter, hive_router as default_hive_router
from mitchell.manager.intent import Intent, parse_fast_intent
from mitchell.tools.registry import Tool, ToolRegistry, tool_registry as default_tool_registry


class Message(BaseModel):
    """Short-term chat message representation."""

    role: str = Field(..., description="Message author role: user, assistant, system, tool")
    content: str = Field(..., description="Message text content")


class Manager:
    """Core Manager coordinating memory, intents, Hive agents, tools, and event logging."""

    def __init__(
        self,
        memory_limit: int = 20,
        tool_registry: Optional[ToolRegistry] = None,
        hive: Optional[HiveRouter] = None,
        events: Optional[EventLog] = None,
    ) -> None:
        self.memory_limit = memory_limit
        self.memory: List[Message] = []
        self.tool_registry = tool_registry or default_tool_registry
        self.hive = hive or default_hive_router
        self.event_log = events or default_event_log

    def add_message(self, role: str, content: str) -> None:
        """Add a message to short-term memory, keeping the last N messages."""
        self.memory.append(Message(role=role, content=content))
        if len(self.memory) > self.memory_limit:
            self.memory = self.memory[-self.memory_limit:]

    def get_history(self) -> List[Message]:
        """Return the short-term message history."""
        return list(self.memory)

    def clear_history(self) -> None:
        """Clear short-term memory."""
        self.memory.clear()

    def receive(self, message: str) -> str:
        """Process incoming user message, log event, and generate response."""
        logger.info("Manager received: {}", message)
        self.add_message(role="user", content=message)
        self.event_log.log_event("user_message", source="cli", data={"message": message})

        # 1. Fast Intent path (rule-based without LLM)
        intent = parse_fast_intent(message)
        if intent:
            response = self._handle_fast_intent(intent)
        else:
            # 2. Fallback placeholder
            response = f"LLM call not implemented yet. You said: {message}"
            self.event_log.log_event("fallback_executed", source="manager", data={"message": message})

        self.add_message(role="assistant", content=response)
        logger.debug("Manager response: {}", response)
        return response

    def _handle_fast_intent(self, intent: Intent) -> str:
        """Handle recognized fast intents."""
        if intent.action_type == "exit":
            self.event_log.log_event("session_exit", source="manager")
            return "[exit] Goodbye!"

        if intent.action_type == "help":
            return (
                "Available Commands:\n"
                "  • help: Show this help message\n"
                "  • list tools / tools: List all registered tools\n"
                "  • call tool <name> <args>: Execute a tool (e.g. 'call tool echo hello')\n"
                "  • list agents / agents: List all registered Hive agents\n"
                "  • agent <id> <msg>: Send a message to a Hive agent (e.g. 'agent echo_agent hello')\n"
                "  • list events: Show recent event log entries\n"
                "  • exit / quit: Exit the session"
            )

        if intent.action_type == "list_tools":
            tools = self.tool_registry.list_tools()
            if not tools:
                return "No tools currently registered."
            lines = ["Registered Tools:"]
            for tool in tools:
                lines.append(f"  • {tool['name']}: {tool['description']}")
            return "\n".join(lines)

        if intent.action_type == "list_agents":
            agents = self.hive.list_agents()
            if not agents:
                return "No agents currently registered in Hive."
            lines = ["Registered Hive Agents:"]
            for agent in agents:
                lines.append(f"  • {agent['agent_id']}: {agent['description']}")
            return "\n".join(lines)

        if intent.action_type == "list_events":
            events = self.event_log.get_recent(5)
            if not events:
                return "Event log is currently empty."
            lines = ["Recent Events:"]
            for ev in events:
                lines.append(f"  [{ev.timestamp.strftime('%H:%M:%S')}] {ev.type} (from {ev.source}): {ev.data}")
            return "\n".join(lines)

        if intent.action_type == "hive_message":
            return self.send_to_hive(intent.agent_name, intent.parameters.get("message", ""))

        if intent.action_type == "call_tool":
            return self.call_tool(intent.tool_name, intent.parameters)

        return f"Unhandled intent: {intent.action_type}"

    def send_to_hive(self, agent_id: Optional[str], message: str) -> str:
        """Send a message to a specific Hive agent via the HiveRouter."""
        if not agent_id:
            return "Error: No agent ID specified."

        logger.info("Manager routing to Hive agent '{}': {}", agent_id, message)
        self.event_log.log_event(
            "hive_dispatch",
            source="manager",
            data={"agent_id": agent_id, "message": message},
        )
        result = self.hive.send_message(agent_id=agent_id, message=message, sender="manager")
        self.event_log.log_event(
            "hive_response",
            source=agent_id,
            data={"response": result},
        )
        return str(result)

    def call_tool(self, tool_name: Optional[str], parameters: Dict[str, Any]) -> str:
        """Call a registered tool by name using the ToolRegistry."""
        if not tool_name:
            return "Error: No tool name specified."

        tool = self.tool_registry.get(tool_name)
        if not tool:
            return f"Error: Tool '{tool_name}' not found in registry."

        try:
            logger.info("Manager invoking tool '{}' with parameters: {}", tool_name, parameters)
            result = self._invoke_tool_function(tool, parameters)
            self.event_log.log_event(
                "tool_executed",
                source="manager",
                data={"tool": tool_name, "parameters": parameters, "result": str(result)},
            )
            return f"[Tool: {tool_name}] Result: {result}"
        except Exception as exc:
            logger.error("Error executing tool '{}': {}", tool_name, exc)
            self.event_log.log_event(
                "tool_error",
                source="manager",
                data={"tool": tool_name, "error": str(exc)},
            )
            return f"[Tool: {tool_name}] Execution error: {exc}"

    def _invoke_tool_function(self, tool: Tool, parameters: Dict[str, Any]) -> Any:
        """Invoke tool callable by binding parameters to function signature."""
        sig = inspect.signature(tool.function)
        accepted_params: Dict[str, Any] = {}
        has_kwargs = any(
            p.kind == inspect.Parameter.VAR_KEYWORD for p in sig.parameters.values()
        )

        for param_name, param in sig.parameters.items():
            if param_name in parameters:
                accepted_params[param_name] = parameters[param_name]
            elif len(sig.parameters) == 1 and (
                param.default == inspect.Parameter.empty
                or param_name in ("input", "text", "message", "query", "value")
            ):
                if "raw" in parameters:
                    accepted_params[param_name] = parameters["raw"]
                elif parameters:
                    accepted_params[param_name] = next(iter(parameters.values()))

        if has_kwargs:
            return tool.function(**parameters)
        if accepted_params:
            return tool.function(**accepted_params)
        if not sig.parameters:
            return tool.function()
        return tool.function(**parameters)


class ManagerLoop:
    """Asynchronous orchestration loop for managing ongoing tasks and agent cycles."""

    def __init__(self, manager: Optional[Manager] = None) -> None:
        self.manager = manager or Manager()
        self.is_running: bool = False

    async def run_step(self, message: Optional[str] = None) -> Optional[str]:
        """Execute a single step in the manager loop."""
        if message:
            return self.manager.receive(message)
        return None

    async def run(self) -> None:
        """Run the manager loop continuously until stopped."""
        self.is_running = True
        while self.is_running:
            await asyncio.sleep(0.1)

    def stop(self) -> None:
        """Signal the manager loop to stop."""
        self.is_running = False


__all__ = ["Message", "Manager", "ManagerLoop"]

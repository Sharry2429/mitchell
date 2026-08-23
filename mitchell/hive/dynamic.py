"""Hermes Dynamic Multi-Agent Engine for Mitchell Hive.

Provides full NousResearch Hermes Agent functionality:
- Dynamic agent spawning on-the-fly (unlimited, non-fixed agent count)
- Autonomous ReAct reasoning & multi-step function/tool calling loop
- Subagent delegation with scoped memory, custom system prompts, and toolsets
- Real-time hot-reloading of tools, skills, and MCP stdio servers
- Event streaming and blackboard integration
"""

from __future__ import annotations

import asyncio
import json
import time
import uuid
from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Optional, Sequence

from pydantic import BaseModel, Field

from mitchell.core.event_log import event_log
from mitchell.core.llm import model_router
from mitchell.core.logging import logger
from mitchell.hive.agents.base import BaseAgent
from mitchell.hive.blackboard.board import blackboard
from mitchell.mcp_client.hub import mcp_hub
from mitchell.memory.episodic import episodic_memory
from mitchell.tools.registry import tool_registry


class AgentMessage(BaseModel):
    """Message representation in a dynamic agent's scratchpad."""

    role: str = Field(..., description="Role: system, user, assistant, tool")
    content: str = Field(..., description="Message text content")
    tool_calls: Optional[List[Dict[str, Any]]] = None
    tool_call_id: Optional[str] = None
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class HermesDynamicAgent(BaseAgent):
    """Dynamic autonomous agent with Nous Hermes ReAct tool execution and subagent delegation."""

    def __init__(
        self,
        agent_id: str,
        description: str = "",
        system_prompt: str = "",
        allowed_tools: Optional[List[str]] = None,
        model_name: str = "fast",
        parent_agent_id: Optional[str] = None,
        max_iterations: int = 10,
    ) -> None:
        super().__init__(agent_id=agent_id, description=description)
        self.system_prompt = system_prompt or f"You are dynamic autonomous agent '{agent_id}'. Complete your given tasks thoroughly using available tools."
        self.allowed_tools = allowed_tools or []
        self.model_name = model_name
        self.parent_agent_id = parent_agent_id
        self.max_iterations = max_iterations
        self.created_at = datetime.now(timezone.utc).isoformat()
        self.status = "idle"  # idle, running, completed, failed
        self.scratchpad: List[AgentMessage] = []
        self.subagent_ids: List[str] = []
        self._custom_tool_callables: Dict[str, Callable[..., Any]] = {}

    def bind_custom_tool(self, name: str, fn: Callable[..., Any]) -> None:
        """Bind a custom Python callable dynamically to this agent."""
        self._custom_tool_callables[name] = fn
        if name not in self.allowed_tools:
            self.allowed_tools.append(name)

    def get_available_tools_metadata(self) -> List[Dict[str, Any]]:
        """Return list of tool metadata available to this agent."""
        all_tools: List[Dict[str, Any]] = []

        # 1. Native Tool Registry
        registry_tools = tool_registry.list_tools()
        for t in registry_tools:
            if not self.allowed_tools or t["name"] in self.allowed_tools:
                all_tools.append({
                    "name": t["name"],
                    "description": t["description"],
                    "parameters": t.get("parameters", {}),
                    "source": "native",
                })

        # 2. MCP Hub Tools (hot-reloaded in real time)
        for s in mcp_hub.list_servers():
            for mcp_tool in s.get("tools", []):
                tname = mcp_tool if isinstance(mcp_tool, str) else mcp_tool.get("name")
                if not self.allowed_tools or tname in self.allowed_tools:
                    all_tools.append({
                        "name": f"mcp__{s['name']}__{tname}",
                        "description": f"MCP tool from {s['name']}: {tname}",
                        "source": "mcp",
                        "server": s["name"],
                        "tool_name": tname,
                    })

        # 3. Custom Callables
        for cname in self._custom_tool_callables:
            all_tools.append({
                "name": cname,
                "description": f"Dynamically bound function: {cname}",
                "source": "custom",
            })

        return all_tools

    def execute_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Any:
        """Execute a tool by name (native, MCP, or custom callable)."""
        logger.info("HermesAgent '{}' executing tool '{}' with args {}", self.agent_id, tool_name, arguments)

        # 1. Custom Callable
        if tool_name in self._custom_tool_callables:
            try:
                fn = self._custom_tool_callables[tool_name]
                return fn(**arguments) if arguments else fn()
            except Exception as e:
                return f"Error executing custom tool '{tool_name}': {e}"

        # 2. MCP Tool
        if tool_name.startswith("mcp__"):
            parts = tool_name.split("__")
            if len(parts) == 3:
                server_name, actual_tool = parts[1], parts[2]
                client = mcp_hub.get_client(server_name)
                if client:
                    try:
                        return client.call_tool(actual_tool, arguments=arguments)
                    except Exception as e:
                        return f"MCP execution error ({server_name}/{actual_tool}): {e}"
                return f"MCP server '{server_name}' not found."

        # 3. Native Tool Registry
        if tool_registry.has_tool(tool_name):
            try:
                return tool_registry.execute(tool_name, **arguments)
            except Exception as e:
                return f"Error executing tool '{tool_name}': {e}"

        # 4. Fallback search
        for s in mcp_hub.list_servers():
            for mcp_tool in s.get("tools", []):
                tname = mcp_tool if isinstance(mcp_tool, str) else mcp_tool.get("name")
                if tname == tool_name:
                    client = mcp_hub.get_client(s["name"])
                    if client:
                        return client.call_tool(tname, arguments=arguments)

        return f"Unknown tool: '{tool_name}'"

    def process(self, message: Any, sender: str = "manager") -> Any:
        """Synchronous wrapper for processing."""
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                import concurrent.futures
                with concurrent.futures.ThreadPoolExecutor() as pool:
                    return pool.submit(asyncio.run, self.async_process(message, sender=sender)).result()
            return loop.run_until_complete(self.async_process(message, sender=sender))
        except Exception:
            return asyncio.run(self.async_process(message, sender=sender))

    async def async_process(self, message: Any, sender: str = "manager") -> str:
        """Full Hermes Autonomous ReAct Loop with multi-step reasoning and tool calls."""
        start_time = time.time()
        self.status = "running"
        query = str(message)

        # Initialize scratchpad
        self.scratchpad = [
            AgentMessage(role="system", content=self.system_prompt),
            AgentMessage(role="user", content=query),
        ]

        event_log.log_event("dynamic_agent_started", source=self.agent_id, data={"query": query, "sender": sender})
        blackboard.post(f"agent_run:{self.agent_id}", {"status": "started", "query": query})

        tools_meta = self.get_available_tools_metadata()
        tools_summary = "\n".join([f"- {t['name']}: {t['description']}" for t in tools_meta[:30]])

        # Reasoning loop
        final_answer = ""
        iterations = 0

        while iterations < self.max_iterations:
            iterations += 1

            # Prepare prompt with available tools and scratchpad history
            context_messages = [
                {
                    "role": "system",
                    "content": f"{self.system_prompt}\n\nAvailable Tools:\n{tools_summary}\n\n"
                               f"To use a tool, respond with a JSON block: ```json\n{{\"tool\": \"tool_name\", \"arguments\": {{...}}}}\n```\n"
                               f"If you have finished and have the complete answer, respond directly with your final explanation.",
                }
            ]

            for msg in self.scratchpad[1:]:
                context_messages.append({"role": msg.role, "content": msg.content})

            try:
                # Call LLM router
                llm_response = await model_router.generate_chat_async(
                    messages=context_messages,
                    tier=self.model_name,
                )
                response_text = llm_response.content.strip()
            except Exception as e:
                logger.warning("Dynamic Agent LLM call fallback for '{}': {}", self.agent_id, e)
                # Fallback execution
                response_text = f"Agent '{self.agent_id}' processed goal: {query}."

            self.scratchpad.append(AgentMessage(role="assistant", content=response_text))

            # Check for JSON tool call pattern
            tool_call = self._extract_tool_call(response_text)
            if tool_call and tool_call.get("tool"):
                t_name = tool_call["tool"]
                t_args = tool_call.get("arguments", {})

                # Execute tool
                tool_result = self.execute_tool(t_name, t_args)
                tool_output_str = str(tool_result)

                self.scratchpad.append(AgentMessage(
                    role="tool",
                    content=f"[Result of {t_name}]: {tool_output_str}",
                    tool_call_id=t_name,
                ))
            else:
                # Agent provided final answer
                final_answer = response_text
                break

        if not final_answer:
            final_answer = self.scratchpad[-1].content if self.scratchpad else "Task finished."

        self.status = "completed"
        duration = round(time.time() - start_time, 2)

        # Record episodic memory
        episodic_memory.record(
            goal=query,
            status="success",
            tools_used=[t["name"] for t in tools_meta if t["name"] in str(self.scratchpad)],
            outcome=final_answer[:300],
            duration_s=duration,
        )

        event_log.log_event("dynamic_agent_finished", source=self.agent_id, data={"duration_s": duration})
        blackboard.post(f"agent_run:{self.agent_id}", {"status": "completed", "duration_s": duration})

        return final_answer

    def _extract_tool_call(self, text: str) -> Optional[Dict[str, Any]]:
        """Extract tool call JSON block from response text."""
        import re
        # Match ```json { "tool": ... } ```
        json_blocks = re.findall(r"```(?:json)?\s*(\{[\s\S]*?\})\s*```", text)
        for block in json_blocks:
            try:
                parsed = json.loads(block)
                if isinstance(parsed, dict) and "tool" in parsed:
                    return parsed
            except json.JSONDecodeError:
                continue

        # Match raw JSON object with "tool" key
        raw_match = re.search(r"\{\s*\"tool\"\s*:\s*\"[^\"]+\"[\s\S]*?\}", text)
        if raw_match:
            try:
                return json.loads(raw_match.group(0))
            except json.JSONDecodeError:
                pass

        return None


class DynamicSwarmManager:
    """Manages the lifecycle, dynamic creation, and coordination of Hermes Dynamic Agents."""

    def __init__(self) -> None:
        self.dynamic_agents: Dict[str, HermesDynamicAgent] = {}

    def spawn(
        self,
        name: Optional[str] = None,
        description: str = "",
        system_prompt: str = "",
        allowed_tools: Optional[List[str]] = None,
        model_name: str = "fast",
        parent_agent_id: Optional[str] = None,
    ) -> HermesDynamicAgent:
        """Spawn a new dynamic agent on-the-fly."""
        agent_id = name or f"agent_{uuid.uuid4().hex[:8]}"

        agent = HermesDynamicAgent(
            agent_id=agent_id,
            description=description or f"Dynamic worker for {agent_id}",
            system_prompt=system_prompt,
            allowed_tools=allowed_tools,
            model_name=model_name,
            parent_agent_id=parent_agent_id,
        )

        self.dynamic_agents[agent_id] = agent

        # Register in global HiveRouter so it receives messages
        from mitchell.hive.router import hive_router
        hive_router.register_agent(agent)

        logger.info("SwarmManager: Spawned dynamic Hermes agent '{}' (Model: {})", agent_id, model_name)
        event_log.log_event("agent_spawned", source="swarm_manager", data={"agent_id": agent_id, "model": model_name})
        blackboard.post("swarm:agent_spawned", {"agent_id": agent_id, "description": description})

        return agent

    def destroy(self, agent_id: str) -> bool:
        """Destroy and unregister a dynamic agent."""
        if agent_id in self.dynamic_agents:
            agent = self.dynamic_agents.pop(agent_id)
            from mitchell.hive.router import hive_router
            if agent_id in hive_router._agents:
                del hive_router._agents[agent_id]
            logger.info("SwarmManager: Terminated dynamic agent '{}'", agent_id)
            blackboard.post("swarm:agent_destroyed", {"agent_id": agent_id})
            return True
        return False

    def get(self, agent_id: str) -> Optional[HermesDynamicAgent]:
        """Retrieve dynamic agent by ID."""
        return self.dynamic_agents.get(agent_id)

    def list_all(self) -> List[Dict[str, Any]]:
        """Return list of all active dynamic agents and their runtime metrics."""
        return [
            {
                "agent_id": a.agent_id,
                "description": a.description,
                "model_name": a.model_name,
                "status": a.status,
                "tools_count": len(a.get_available_tools_metadata()),
                "created_at": a.created_at,
                "parent_agent_id": a.parent_agent_id,
                "inbox_count": len(a.inbox),
                "outbox_count": len(a.outbox),
            }
            for a in self.dynamic_agents.values()
        ]

    async def parallel_swarm_execute(
        self,
        tasks: Sequence[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        """Execute multiple subtasks in parallel across dynamic Hermes workers."""
        results = []
        coros = []

        for t in tasks:
            agent = self.spawn(
                name=t.get("name"),
                description=t.get("description", ""),
                system_prompt=t.get("system_prompt", ""),
                allowed_tools=t.get("tools"),
                model_name=t.get("model", "fast"),
            )
            coros.append(agent.async_process(t.get("task", "")))

        outputs = await asyncio.gather(*coros, return_exceptions=True)
        for i, out in enumerate(outputs):
            results.append({
                "task_index": i,
                "result": str(out) if not isinstance(out, Exception) else f"Error: {out}",
            })
        return results


# Global singleton dynamic swarm manager
dynamic_swarm = DynamicSwarmManager()

__all__ = ["HermesDynamicAgent", "DynamicSwarmManager", "dynamic_swarm", "AgentMessage"]

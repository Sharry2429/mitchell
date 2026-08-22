"""Full Manager Decision Loop integrating Thinking, Planning, Critic, LLM Council, Memory, and Hive."""

import asyncio
import inspect
import time
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from mitchell.core.cost import cost_tracker
from mitchell.core.event_log import EventLog, event_log as default_event_log
from mitchell.core.llm import model_router
from mitchell.core.logging import logger
from mitchell.hive.router import HiveRouter, hive_router as default_hive_router
from mitchell.manager.classifier import GoalClassifier, goal_classifier as default_classifier
from mitchell.manager.council import LLMCouncil, llm_council as default_council
from mitchell.manager.critic import PlanCritic, plan_critic as default_critic
from mitchell.manager.intent import Intent, parse_fast_intent
from mitchell.manager.planner import TaskGraph, TaskPlanner, task_planner as default_planner
from mitchell.memory.episodic import EpisodicMemory, episodic_memory as default_episodic_memory
from mitchell.memory.long_term import LongTermMemory, long_term_memory as default_long_term_memory
from mitchell.memory.self_model import SelfModel, self_model as default_self_model
from mitchell.skills.executor import SkillExecutor, skill_executor as default_skill_executor
from mitchell.skills.library import SkillLibrary, skill_library as default_skill_library
from mitchell.tools.registry import Tool, ToolRegistry, tool_registry as default_tool_registry


class Message(BaseModel):
    """Short-term chat message representation."""

    role: str = Field(..., description="Message author role: user, assistant, system, tool")
    content: str = Field(..., description="Message text content")


class Manager:
    """Full Manager Decision Loop coordinating Thinking, Planning, Memory, Hive, and Cloud LLM Routing."""

    def __init__(
        self,
        memory_limit: int = 20,
        tool_registry: Optional[ToolRegistry] = None,
        hive: Optional[HiveRouter] = None,
        events: Optional[EventLog] = None,
        long_term: Optional[LongTermMemory] = None,
        episodic: Optional[EpisodicMemory] = None,
        self_mod: Optional[SelfModel] = None,
        skills: Optional[SkillLibrary] = None,
        skill_exec: Optional[SkillExecutor] = None,
        classifier: Optional[GoalClassifier] = None,
        planner: Optional[TaskPlanner] = None,
        critic: Optional[PlanCritic] = None,
        council: Optional[LLMCouncil] = None,
    ) -> None:
        self.memory_limit = memory_limit
        self.memory: List[Message] = []
        self.tool_registry = tool_registry or default_tool_registry
        self.hive = hive or default_hive_router
        self.event_log = events or default_event_log
        self.long_term = long_term or default_long_term_memory
        self.episodic = episodic or default_episodic_memory
        self.self_model = self_mod or default_self_model
        self.skills = skills or default_skill_library
        self.skill_executor = skill_exec or default_skill_executor
        self.classifier = classifier or default_classifier
        self.planner = planner or default_planner
        self.critic = critic or default_critic
        self.council = council or default_council
        self.router = model_router

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
        """Execute the Full Manager Decision Loop for incoming goals."""
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                import concurrent.futures
                with concurrent.futures.ThreadPoolExecutor() as pool:
                    return pool.submit(asyncio.run, self._async_receive(message)).result()
            return loop.run_until_complete(self._async_receive(message))
        except Exception:
            return asyncio.run(self._async_receive(message))

    run = receive

    async def _async_receive(self, message: str) -> str:
        """Asynchronous decision loop."""
        start_time = time.time()
        logger.info("Manager received: {}", message)
        self.add_message(role="user", content=message)
        self.event_log.log_event("user_message", source="cli", data={"message": message})

        tools_used: List[str] = []

        # 1. Fast Intent Path (rule-based shortcut)
        intent = parse_fast_intent(message)
        if intent:
            response = self._handle_fast_intent(intent, tools_used=tools_used)
            duration = round(time.time() - start_time, 2)
            self._finalize_run(message, response, tools_used, duration)
            return response

        # 2. Context Retrieval (RAG over Long-Term Memory & Skill Library)
        mem_matches = self.long_term.search(message, top_k=2)
        skill_matches = self.skills.search_skills(message, top_k=2)

        # 3. Goal Classification
        classification = self.classifier.classify(message)
        logger.info(
            "Manager: Goal classified as '{}' ({}), Requires Council: {}",
            classification.domain,
            classification.complexity,
            classification.requires_council,
        )

        # 4. Structured Plan Synthesis (TaskGraph)
        plan = await self.planner.create_plan(
            goal=message,
            classification=classification,
            memory_context=mem_matches,
        )

        # 5. Critic Pass (Safety & Karpathy principles check)
        critic_review = self.critic.evaluate(plan)
        if not critic_review.approved:
            response = f"Plan rejected by safety critic: {', '.join(critic_review.critiques)}"
            duration = round(time.time() - start_time, 2)
            self._finalize_run(message, response, tools_used, duration)
            return response

        # 6. Selective LLM Council (Triggered only on high-stakes / ambiguous tasks)
        if classification.requires_council:
            council_res = await self.council.deliberate(topic=message, proposed_action=str(plan.nodes))
            if not council_res.approved_for_execution:
                response = f"Council declined action: {council_res.chairman_summary}"
                duration = round(time.time() - start_time, 2)
                self._finalize_run(message, response, tools_used, duration)
                return response

        # 7. Execute Subtasks through Hive Workers
        results: List[str] = []
        for node in plan.nodes:
            logger.info("Manager dispatching subtask '{}' to Hive agent '{}'", node.title, node.target_agent)
            tools_used.append(node.target_agent)
            agent_res = self.hive.send_message(
                agent_id=node.target_agent,
                message=node.payload or node.action,
                sender="manager",
            )
            results.append(f"[{node.title}]: {agent_res}")

        response = "\n".join(results) if results else "Execution completed."
        duration = round(time.time() - start_time, 2)
        self._finalize_run(message, response, tools_used, duration)
        return response

    def _finalize_run(self, message: str, response: str, tools_used: List[str], duration: float) -> None:
        """Record outcome, update memory, and log telemetry."""
        self.add_message(role="assistant", content=response)
        cost_summary = cost_tracker.get_summary()

        self.episodic.record(
            goal=message,
            status="success" if not response.startswith("Error") and not response.startswith("Plan rejected") else "failed",
            tools_used=tools_used,
            outcome=response[:300],
            duration_s=duration,
        )

    def _handle_fast_intent(self, intent: Intent, tools_used: Optional[List[str]] = None) -> str:
        """Handle recognized fast intents."""
        if intent.action_type == "exit":
            self.event_log.log_event("session_exit", source="manager")
            return "[exit] Goodbye!"

        if intent.action_type == "help":
            return (
                "Available Commands:\n"
                "  • help: Show this help message\n"
                "  • list tools / tools: List all registered tools\n"
                "  • list skills / skills: List procedural skills\n"
                "  • run skill <name> <params>: Execute a skill\n"
                "  • remember <category> <key> <content>: Save to Long-Term Memory\n"
                "  • recall <category> <key>: Recall from Long-Term Memory\n"
                "  • self model: Show Mitchell's capabilities and stats\n"
                "  • cost / budget: Show token usage and cost in INR\n"
                "  • list agents: List all registered Hive agents\n"
                "  • agent <id> <msg>: Send message to Hive agent\n"
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

        if intent.action_type == "list_skills":
            skills = self.skills.list_skills()
            if not skills:
                return "No skills currently in library."
            lines = ["Registered Procedural Skills:"]
            for s in skills:
                lines.append(f"  • {s.name} (v{s.version}, {len(s.steps)} steps): {s.description}")
            return "\n".join(lines)

        if intent.action_type == "run_skill":
            if tools_used is not None:
                tools_used.append(f"skill:{intent.skill_name}")
            res = self.skill_executor.execute(intent.skill_name, parameters=intent.parameters)
            if res.get("success"):
                return f"[Skill: {intent.skill_name}] Completed in {res.get('duration_s')}s"
            return f"[Skill: {intent.skill_name}] Failed: {res.get('error')}"

        if intent.action_type == "remember":
            params = intent.parameters
            cat = params.get("category", "general")
            k = params.get("key", "info")
            content = params.get("content", "")
            entry = self.long_term.remember(category=cat, key=k, content=content)
            return f"[Memory] Stored [{entry.category}] {entry.key} -> '{entry.content}'"

        if intent.action_type == "recall":
            params = intent.parameters
            if "query" in params:
                matches = self.long_term.search(params["query"], top_k=3)
                if not matches:
                    return f"No memories found matching '{params['query']}'"
                lines = [f"Found {len(matches)} matching memories:"]
                for m in matches:
                    lines.append(f"  • {m['text']} (relevance: {m['similarity']:.2f})")
                return "\n".join(lines)
            else:
                cat = params.get("category", "")
                k = params.get("key", "")
                val = self.long_term.recall(cat, k)
                if val:
                    return f"[Memory: {cat}:{k}] {val}"
                return f"No memory found for [{cat}:{k}]"

        if intent.action_type == "self_model":
            caps = self.self_model.list_all()
            cost = cost_tracker.get_summary()
            lines = ["Self-Model Capabilities & Confidence:"]
            for c in caps:
                lines.append(f"  • {c.capability_name} ({c.category}) | Confidence: {c.confidence:.2f} | Success Rate: {c.success_rate}%")
            lines.append(f"\nCost Status: Today {cost['today_spent_inr']} / Total {cost['total_spent_inr']} (Budget: {cost['budget_status']})")
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
            if tools_used is not None:
                tools_used.append(f"agent:{intent.agent_name}")
            return self.send_to_hive(intent.agent_name, intent.parameters.get("message", ""))

        if intent.action_type == "call_tool":
            if tools_used is not None:
                tools_used.append(intent.tool_name or "unknown")
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
            data={"response": str(result)[:300]},
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
                or param_name in ("input", "text", "message", "query", "value", "cmd", "url", "title")
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

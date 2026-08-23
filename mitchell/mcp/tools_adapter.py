"""MCP Tools Adapter — Aggregates all Mitchell capabilities into MCP Tool Specifications.

Ensures 100% of Mitchell's multi-pillar tools (System, IDE, Browser, Desktop UIA, Android,
IoT, Documents, Research, Multi-Agent Harness, Teaching, Takeover) are exposed as MCP tools.
"""

import inspect
import json
from typing import Any, Callable, Dict, List, Optional

from mitchell.core.event_log import event_log
from mitchell.core.logging import logger
from mitchell.mcp.protocol import MCPTextContent, MCPTool, MCPToolResult
from mitchell.tools.registry import Tool, tool_registry


class MCPToolAdapter:
    """Adapts internal Mitchell tool functions into standard MCP tool schemas and handlers."""

    def __init__(self) -> None:
        self.tool_reg = tool_registry
        self.tool_reg.discover()
        self._extra_tools: Dict[str, Tool] = {}
        self._register_subsystem_tools()

    def _register_subsystem_tools(self) -> None:
        """Register specialized tools for Deep Research, Real Browser, Harness, IoT, Documents, Takeover."""
        # 1. Deep Research Tool
        from mitchell.browser.deep_research import deep_research_engine
        def tool_deep_research(query: str, max_sources: int = 4) -> str:
            import asyncio
            res = asyncio.run(deep_research_engine.execute_research(query=query, max_sources=max_sources))
            return f"Research Findings:\n{res.detailed_report}\nKey Points: {json.dumps(res.key_findings)}"

        self._add_tool(
            name="deep_research_execute",
            description="Execute autonomous Perplexity-style multi-source deep research with citations.",
            parameters={
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Research question or technical topic"},
                    "max_sources": {"type": "integer", "description": "Max web sources to verify", "default": 4},
                },
                "required": ["query"],
            },
            func=tool_deep_research,
        )

        # 2. Real Browser Profile Attach Tool
        from mitchell.browser.cdp_attach import real_browser_manager
        def tool_browser_real_attach(profile_directory: str = "Default", headless: bool = False) -> str:
            import asyncio
            res = asyncio.run(real_browser_manager.attach_real_profile(profile_directory=profile_directory, headless=headless))
            return json.dumps(res, indent=2)

        self._add_tool(
            name="browser_real_profile_attach",
            description="Attach Playwright CDP session to user's real Chrome/Edge profile (preserving cookies, logins, extensions).",
            parameters={
                "type": "object",
                "properties": {
                    "profile_directory": {"type": "string", "description": "User profile folder (e.g. Default)", "default": "Default"},
                    "headless": {"type": "boolean", "description": "Run in headless mode", "default": False},
                },
            },
            func=tool_browser_real_attach,
        )

        # 3. Windows UIA Structural Click/Type Tools
        from mitchell.windows.uia_driver import windows_uia_driver
        def tool_windows_uia_click(app_title: str, element_name: str) -> str:
            res = windows_uia_driver.click_element_by_name(app_title_substring=app_title, element_name=element_name)
            return json.dumps(res, indent=2)

        def tool_windows_uia_type(app_title: str, element_name: str, text: str) -> str:
            res = windows_uia_driver.type_into_element(app_title_substring=app_title, element_name=element_name, text=text)
            return json.dumps(res, indent=2)

        self._add_tool(
            name="windows_uia_click",
            description="Find and click a structural UI element in an open Windows application using UI Automation (UIA).",
            parameters={
                "type": "object",
                "properties": {
                    "app_title": {"type": "string", "description": "Target window title substring"},
                    "element_name": {"type": "string", "description": "Accessible name or automation ID of button/control"},
                },
                "required": ["app_title", "element_name"],
            },
            func=tool_windows_uia_click,
        )
        self._add_tool(
            name="windows_uia_type",
            description="Type text into a named input field in a Windows application using UI Automation.",
            parameters={
                "type": "object",
                "properties": {
                    "app_title": {"type": "string", "description": "Target window title substring"},
                    "element_name": {"type": "string", "description": "Accessible name of text field"},
                    "text": {"type": "string", "description": "Text to enter"},
                },
                "required": ["app_title", "element_name", "text"],
            },
            func=tool_windows_uia_type,
        )

        # 4. Multi-Agent Coding Harness Tool
        from mitchell.ide.agent_harness import agent_harness
        def tool_agent_harness_dispatch(agent_id: str, prompt: str) -> str:
            import asyncio
            session = asyncio.run(agent_harness.start_agent_task(agent_id=agent_id, prompt=prompt))
            return f"Dispatched task to {session.display_name} (Session: {session.session_id}, Status: {session.status})"

        self._add_tool(
            name="agent_harness_dispatch",
            description="Dispatch a coding task to external CLI agents (Claude Code, Grok, Antigravity, OpenCode, Codex).",
            parameters={
                "type": "object",
                "properties": {
                    "agent_id": {"type": "string", "description": "Agent identifier: claude | grok | antigravity | opencode | codex"},
                    "prompt": {"type": "string", "description": "Goal or instruction for the coding agent"},
                },
                "required": ["agent_id", "prompt"],
            },
            func=tool_agent_harness_dispatch,
        )

        # 5. Smart Home / IoT Tools
        from mitchell.iot.homeassistant import homeassistant_client
        def tool_iot_call_service(domain: str, service: str, entity_id: str) -> str:
            import asyncio
            res = asyncio.run(homeassistant_client.call_service(domain=domain, service=service, entity_id=entity_id))
            return json.dumps(res, indent=2)

        def tool_iot_get_states() -> str:
            import asyncio
            states = asyncio.run(homeassistant_client.get_states())
            return json.dumps([s.model_dump() for s in states], indent=2)

        self._add_tool(
            name="iot_call_service",
            description="Control a Smart Home / Home Assistant entity (e.g. turn on light, adjust AC climate).",
            parameters={
                "type": "object",
                "properties": {
                    "domain": {"type": "string", "description": "Domain (light, switch, climate, lock)"},
                    "service": {"type": "string", "description": "Service (turn_on, turn_off, set_temperature)"},
                    "entity_id": {"type": "string", "description": "Entity ID (e.g. light.living_room)"},
                },
                "required": ["domain", "service", "entity_id"],
            },
            func=tool_iot_call_service,
        )
        self._add_tool(
            name="iot_get_states",
            description="Query live states of all smart home devices in Home Assistant.",
            parameters={"type": "object", "properties": {}},
            func=tool_iot_get_states,
        )

        # 6. Native Document Tools
        from mitchell.workspace.documents import document_engine
        def tool_document_generate_report(topic: str, content: Optional[str] = None) -> str:
            doc = document_engine.generate_report(topic=topic, content_markdown=content)
            return f"Generated Document '{doc.title}' (ID: {doc.doc_id}) in Workspace."

        self._add_tool(
            name="document_generate_report",
            description="Generate a formatted executive report or technical document inside Mitchell Studio.",
            parameters={
                "type": "object",
                "properties": {
                    "topic": {"type": "string", "description": "Report topic or title"},
                    "content": {"type": "string", "description": "Optional markdown content"},
                },
                "required": ["topic"],
            },
            func=tool_document_generate_report,
        )

        # 7. Takeover Mode Tool
        from mitchell.action.takeover import takeover_engine
        def tool_takeover_start(goal: str) -> str:
            session = takeover_engine.start_takeover(goal=goal)
            return f"Autonomous Takeover Started: Session '{session.session_id}' ({len(session.steps)} steps planned)."

        self._add_tool(
            name="takeover_start_task",
            description="Initiate autonomous task takeover with checkpoint verification and approval gates.",
            parameters={
                "type": "object",
                "properties": {
                    "goal": {"type": "string", "description": "High level project goal to take over and finish"},
                },
                "required": ["goal"],
            },
            func=tool_takeover_start,
        )

    def _add_tool(self, name: str, description: str, parameters: Dict[str, Any], func: Callable) -> None:
        """Register custom tool object."""
        tool = Tool(
            name=name,
            description=description,
            parameters=parameters,
            function=func,
        )
        self._extra_tools[name] = tool

    def list_mcp_tools(self) -> List[MCPTool]:
        """Return all tools formatted according to MCP schema."""
        mcp_tools: List[MCPTool] = []

        # From ToolRegistry
        for t in self.tool_reg.list_tools():
            tool_obj = self.tool_reg.get(t["name"])
            schema = tool_obj.parameters if tool_obj else {"type": "object", "properties": {}}
            mcp_tools.append(
                MCPTool(
                    name=t["name"],
                    description=t["description"],
                    inputSchema=schema,
                )
            )

        # From Extra Subsystems
        for name, tool_obj in self._extra_tools.items():
            if not any(m.name == name for m in mcp_tools):
                mcp_tools.append(
                    MCPTool(
                        name=name,
                        description=tool_obj.description,
                        inputSchema=tool_obj.parameters,
                    )
                )

        return mcp_tools

    def execute_tool(self, name: str, arguments: Dict[str, Any]) -> MCPToolResult:
        """Execute tool by name and return standard MCP result."""
        tool = self.tool_reg.get(name) or self._extra_tools.get(name)
        if not tool:
            return MCPToolResult(
                content=[MCPTextContent(text=f"Error: Tool '{name}' not found in Mitchell MCP registry.")],
                isError=True,
            )

        try:
            logger.info("Executing MCP Tool '{}' with args: {}", name, arguments)
            if inspect.iscoroutinefunction(tool.function):
                import asyncio
                res = asyncio.run(tool(**arguments))
            else:
                res = tool(**arguments)

            event_log.log_event("mcp_tool_executed", source="mcp_adapter", data={"tool": name, "args": arguments})
            return MCPToolResult(
                content=[MCPTextContent(text=str(res))],
                isError=False,
            )
        except Exception as e:
            logger.error("Error executing MCP tool '{}': {}", name, e)
            return MCPToolResult(
                content=[MCPTextContent(text=f"Tool Execution Error: {str(e)}")],
                isError=True,
            )


mcp_tool_adapter = MCPToolAdapter()

__all__ = ["MCPToolAdapter", "mcp_tool_adapter"]

"""Self-evolution and daemon management tools for Mitchell ToolRegistry."""

import json
from typing import Any, Dict

from mitchell.evolution.engine import evolution_engine
from mitchell.evolution.inspector import code_inspector
from mitchell.evolution.synthesizer import tool_synthesizer
from mitchell.daemon.queue import daemon_queue
from mitchell.daemon.scheduler import cron_scheduler
from mitchell.tools.registry import Tool


def tool_self_inspect() -> str:
    """Inspect Mitchell's internal codebase, tools, and architecture."""
    summary = code_inspector.get_system_summary()
    return json.dumps(summary, indent=2)


def tool_self_synthesize_tool(name: str, description: str, parameters_json: str, function_code: str) -> str:
    """Synthesize and register a new Python tool dynamically."""
    try:
        params = json.loads(parameters_json)
    except Exception:
        params = {"type": "object", "properties": {}}

    res = evolution_engine.evolve_tool(
        name=name,
        description=description,
        parameters=params,
        function_code=function_code,
        verify_tests=False,
    )
    return json.dumps(res, indent=2)


def tool_daemon_enqueue(goal: str, priority: int = 10) -> str:
    """Enqueue an autonomous goal into the 24/7 background butler queue."""
    task_id = daemon_queue.enqueue(goal=goal, priority=priority)
    return f"Task '{task_id}' enqueued successfully for goal: {goal}"


def tool_schedule_cron(job_id: str, cron_expr: str, goal: str) -> str:
    """Register a recurring task with a 5-field cron expression."""
    cron_scheduler.add_job(job_id=job_id, cron_expr=cron_expr, goal=goal)
    return f"Cron job '{job_id}' registered: '{cron_expr}' -> '{goal}'"


inspect_tool = Tool(
    name="self_inspect_codebase",
    description="Inspect Mitchell's internal codebase structure, packages, and registered tools.",
    parameters={"type": "object", "properties": {}},
    function=tool_self_inspect,
)

synthesize_tool = Tool(
    name="self_synthesize_tool",
    description="Synthesize, validate, and dynamically register a new Python tool.",
    parameters={
        "type": "object",
        "properties": {
            "name": {"type": "string", "description": "Name of the new tool"},
            "description": {"type": "string", "description": "Description of tool behavior"},
            "parameters_json": {"type": "string", "description": "JSON schema for tool parameters"},
            "function_code": {"type": "string", "description": "Full Python code of the function"},
        },
        "required": ["name", "description", "function_code"],
    },
    function=tool_self_synthesize_tool,
)

enqueue_tool = Tool(
    name="daemon_enqueue_goal",
    description="Enqueue a goal into the 24/7 autonomous daemon queue.",
    parameters={
        "type": "object",
        "properties": {
            "goal": {"type": "string", "description": "Goal for autonomous execution"},
            "priority": {"type": "integer", "description": "Priority (higher runs first)"},
        },
        "required": ["goal"],
    },
    function=tool_daemon_enqueue,
)

schedule_tool = Tool(
    name="daemon_schedule_cron",
    description="Schedule a recurring autonomous routine with 5-field cron expression.",
    parameters={
        "type": "object",
        "properties": {
            "job_id": {"type": "string", "description": "Unique identifier for job"},
            "cron_expr": {"type": "string", "description": "5-field cron expression (e.g. '0 8 * * *')"},
            "goal": {"type": "string", "description": "Goal to execute upon cron trigger"},
        },
        "required": ["job_id", "cron_expr", "goal"],
    },
    function=tool_schedule_cron,
)

TOOLS = [inspect_tool, synthesize_tool, enqueue_tool, schedule_tool]

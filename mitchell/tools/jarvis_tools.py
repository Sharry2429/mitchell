"""JARVIS & Hardware Telemetry tools for the Mitchell ToolRegistry."""

import json
from typing import Any, Dict, Optional

from mitchell.jarvis import executive_briefing, executive_persona, system_telemetry
from mitchell.tools.registry import Tool


def tool_jarvis_get_telemetry() -> str:
    """Get real-time CPU, RAM, Disk, and Battery hardware metrics."""
    metrics = system_telemetry.get_system_metrics()
    return json.dumps(metrics.model_dump(mode="json"), indent=2)


def tool_jarvis_get_daily_briefing(user_name: str = "Sir") -> str:
    """Generate executive daily briefing report across hardware, calendar, tasks, and comms."""
    briefing = executive_briefing.generate_briefing(user_name=user_name)
    return executive_briefing.format_markdown(briefing)


def tool_jarvis_get_spoken_briefing(user_name: str = "Sir") -> str:
    """Generate a spoken audio script briefing for text-to-speech."""
    briefing = executive_briefing.generate_briefing(user_name=user_name)
    return briefing.spoken_summary


telemetry_tool = Tool(
    name="jarvis_get_telemetry",
    description="Retrieve live CPU, RAM, Disk, and Battery hardware metrics.",
    parameters={"type": "object", "properties": {}},
    function=tool_jarvis_get_telemetry,
)

briefing_tool = Tool(
    name="jarvis_daily_briefing",
    description="Generate comprehensive executive intelligence daily briefing (hardware, calendar, tasks, messages).",
    parameters={
        "type": "object",
        "properties": {
            "user_name": {"type": "string", "description": "User title or name to address (default: 'Sir')"}
        },
    },
    function=tool_jarvis_get_daily_briefing,
)

spoken_briefing_tool = Tool(
    name="jarvis_spoken_briefing",
    description="Generate a natural speech script for daily audio briefing.",
    parameters={
        "type": "object",
        "properties": {
            "user_name": {"type": "string", "description": "User name to address"}
        },
    },
    function=tool_jarvis_get_spoken_briefing,
)

TOOLS = [
    telemetry_tool,
    briefing_tool,
    spoken_briefing_tool,
]

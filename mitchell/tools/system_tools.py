"""Dynamic System & Live Telemetry tools for the Mitchell ToolRegistry."""

import json
from typing import Any, Dict, Optional

from mitchell.system import dynamic_briefing, live_system_monitor
from mitchell.tools.registry import Tool


def tool_system_get_telemetry() -> str:
    """Get live real-time CPU, RAM, Disk, active processes, and battery telemetry."""
    metrics = live_system_monitor.get_live_metrics()
    return json.dumps(metrics.model_dump(mode="json"), indent=2)


def tool_system_generate_briefing(user_name: str = "User") -> str:
    """Dynamically synthesize an executive daily briefing across live hardware, git repo status, workspace tasks, and unread comms."""
    briefing = dynamic_briefing.generate_briefing_sync(user_name=user_name)
    return dynamic_briefing.format_markdown(briefing)


def tool_system_spoken_briefing(user_name: str = "User") -> str:
    """Generate a spoken speech script for dynamic audio daily briefing."""
    briefing = dynamic_briefing.generate_briefing_sync(user_name=user_name)
    return briefing.spoken_summary


telemetry_tool = Tool(
    name="system_get_telemetry",
    description="Retrieve live CPU, RAM, Disk, and active process hardware metrics.",
    parameters={"type": "object", "properties": {}},
    function=tool_system_get_telemetry,
)

briefing_tool = Tool(
    name="system_generate_briefing",
    description="Dynamically synthesize an intelligence briefing across live hardware, git repo status, workspace tasks, and unread comms.",
    parameters={
        "type": "object",
        "properties": {
            "user_name": {"type": "string", "description": "User title or name to address"}
        },
    },
    function=tool_system_generate_briefing,
)

spoken_briefing_tool = Tool(
    name="system_spoken_briefing",
    description="Generate a natural speech script for live daily audio briefing.",
    parameters={
        "type": "object",
        "properties": {
            "user_name": {"type": "string", "description": "User name to address"}
        },
    },
    function=tool_system_spoken_briefing,
)

TOOLS = [
    telemetry_tool,
    briefing_tool,
    spoken_briefing_tool,
]

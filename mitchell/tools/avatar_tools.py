"""Avatar, Screen Annotation, and Action Recording tools for Mitchell ToolRegistry."""

import json
from typing import Any, Dict, Optional

from mitchell.avatar.annotator import screen_annotator
from mitchell.avatar.recorder import session_recorder
from mitchell.avatar.state import AvatarStateEnum, avatar_manager
from mitchell.tools.registry import Tool


def tool_avatar_set_state(state_name: str, emotion: Optional[str] = None) -> str:
    """Set the visual expression state of Mitchell's 3D Avatar (idle, listening, thinking, speaking, action, error)."""
    try:
        enum_val = AvatarStateEnum(state_name.lower())
    except ValueError:
        enum_val = AvatarStateEnum.IDLE

    avatar_manager.set_state(enum_val, emotion=emotion)
    return f"Avatar state updated to: {enum_val.value}"


def tool_avatar_highlight(x: int, y: int, width: int = 120, height: int = 40, label: str = "") -> str:
    """Visually highlight a screen region with an on-screen bounding box."""
    ann = screen_annotator.highlight_element(x=x, y=y, width=width, height=height, label=label)
    return f"Highlighted screen region at ({x}, {y}) [{label}]"


def tool_avatar_record_step(action_type: str, target: str, description: str) -> str:
    """Record an action step in the active walkthrough timeline."""
    step = session_recorder.record_step(action_type=action_type, target=target, description=description)
    return f"Recorded step #{step.step_number}: {action_type} -> {target}"


set_state_tool = Tool(
    name="avatar_set_state",
    description="Update 3D Avatar expression state (idle, listening, thinking, speaking, action, error).",
    parameters={
        "type": "object",
        "properties": {
            "state_name": {"type": "string", "description": "State name (idle, listening, thinking, speaking, action, error)"},
            "emotion": {"type": "string", "description": "Optional emotion tag (curious, witty, analytical, confident)"},
        },
        "required": ["state_name"],
    },
    function=tool_avatar_set_state,
)

highlight_tool = Tool(
    name="avatar_highlight_region",
    description="Draw on-screen visual highlight box around coordinates.",
    parameters={
        "type": "object",
        "properties": {
            "x": {"type": "integer", "description": "X coordinate"},
            "y": {"type": "integer", "description": "Y coordinate"},
            "width": {"type": "integer", "description": "Box width in px"},
            "height": {"type": "integer", "description": "Box height in px"},
            "label": {"type": "string", "description": "Label text"},
        },
        "required": ["x", "y"],
    },
    function=tool_avatar_highlight,
)

record_step_tool = Tool(
    name="avatar_record_step",
    description="Log execution step into automated walkthrough timeline.",
    parameters={
        "type": "object",
        "properties": {
            "action_type": {"type": "string", "description": "Type of action (click, type, navigate)"},
            "target": {"type": "string", "description": "Target element or URL"},
            "description": {"type": "string", "description": "Explanation of what was done"},
        },
        "required": ["action_type", "target", "description"],
    },
    function=tool_avatar_record_step,
)

TOOLS = [set_state_tool, highlight_tool, record_step_tool]

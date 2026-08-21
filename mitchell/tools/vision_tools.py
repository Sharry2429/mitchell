"""Multimodal Vision and Visual UI Grounding tools for Mitchell ToolRegistry."""

from mitchell.tools.registry import Tool
from mitchell.vision.grounding import visual_grounder


def vision_locate_element(description: str) -> str:
    """Visually ground a natural language UI element description to screen (x, y) coordinates."""
    coords = visual_grounder.find_coordinates(description)
    if coords:
        return f"Element '{description}' grounded at screen coordinates ({coords[0]}, {coords[1]})"
    return f"Failed to visually ground '{description}'"


def vision_click_desktop(description: str) -> str:
    """Locate a UI element on Windows desktop and click it using human Bezier mouse curve."""
    res = visual_grounder.click_desktop_element(description)
    if res.get("success"):
        c = res.get("clicked_coordinates", {})
        return f"Successfully clicked '{description}' at ({c.get('x')}, {c.get('y')})"
    return f"Failed to click '{description}': {res.get('error')}"


def vision_tap_android(description: str) -> str:
    """Locate a UI element on connected Android screen and tap it with human touch."""
    res = visual_grounder.tap_android_element(description)
    if res.get("success"):
        c = res.get("tapped_coordinates", {})
        return f"Successfully tapped '{description}' on Android screen at ({c.get('x')}, {c.get('y')})"
    return f"Failed to tap '{description}'"


# Tool definitions
locate_tool = Tool(
    name="vision_locate_element",
    description="Find screen pixel coordinates (X, Y) for a described UI element.",
    parameters={
        "type": "object",
        "properties": {
            "description": {"type": "string", "description": "Description of UI element (e.g. 'search bar', 'close button')"}
        },
        "required": ["description"],
    },
    function=vision_locate_element,
)

click_tool = Tool(
    name="vision_click_desktop",
    description="Visually locate an element on desktop and click it with human Bezier mouse path.",
    parameters={
        "type": "object",
        "properties": {
            "description": {"type": "string", "description": "Element description to click"}
        },
        "required": ["description"],
    },
    function=vision_click_desktop,
)

tap_tool = Tool(
    name="vision_tap_android",
    description="Visually locate an element on Android screen and tap it.",
    parameters={
        "type": "object",
        "properties": {
            "description": {"type": "string", "description": "Element description to tap"}
        },
        "required": ["description"],
    },
    function=vision_tap_android,
)

TOOLS = [locate_tool, click_tool, tap_tool]

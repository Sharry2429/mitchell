"""Native Windows automation tools for Mitchell ToolRegistry."""

from typing import Optional
from mitchell.tools.registry import Tool
from mitchell.windows.engine import windows_engine


def windows_launch_app(cmd: str) -> str:
    """Launch a Windows application executable or command."""
    res = windows_engine.launch_app(cmd)
    if res.get("success"):
        return f"Successfully launched '{cmd}' (PID: {res.get('pid')})"
    return f"Failed to launch '{cmd}': {res.get('error')}"


def windows_focus_window(title: str) -> str:
    """Bring a window to focus by title."""
    res = windows_engine.focus_window(title)
    if res.get("success"):
        return f"Successfully focused window '{res.get('title')}'"
    return f"Failed to focus window '{title}': {res.get('error')}"


def windows_click_element(name: str, title: Optional[str] = None) -> str:
    """Click a UI element in a window using human desktop mouse."""
    res = windows_engine.click_element(title_query=title, name=name, human=True)
    if res.get("success"):
        return f"Successfully clicked element '{res.get('element')}' ({res.get('control_type')})"
    return f"Failed to click element '{name}': {res.get('error')}"


def windows_type_text(text: str, title: Optional[str] = None) -> str:
    """Type text into a focused window or control."""
    res = windows_engine.type_text(text=text, title_query=title, human=True)
    if res.get("success"):
        return f"Successfully typed {res.get('text_length')} characters into window"
    return f"Failed to type text: {res.get('error')}"


def windows_list_windows() -> str:
    """List all visible top-level Windows desktop windows."""
    windows = windows_engine.list_windows()
    if not windows:
        return "No visible top-level windows found."
    lines = ["Visible Windows:"]
    for win in windows[:15]:
        lines.append(f"  • [{win['class_name']}] \"{win['title']}\" (PID: {win['process_id']})")
    return "\n".join(lines)


# Tool definitions
launch_tool = Tool(
    name="windows_launch_app",
    description="Launch a desktop Windows application.",
    parameters={
        "type": "object",
        "properties": {
            "cmd": {"type": "string", "description": "Application executable path or command (e.g. 'notepad.exe', 'calc.exe')"}
        },
        "required": ["cmd"],
    },
    function=windows_launch_app,
)

focus_tool = Tool(
    name="windows_focus_window",
    description="Focus and bring a Windows application window to the foreground.",
    parameters={
        "type": "object",
        "properties": {
            "title": {"type": "string", "description": "Window title substring to search and focus"}
        },
        "required": ["title"],
    },
    function=windows_focus_window,
)

click_win_tool = Tool(
    name="windows_click_element",
    description="Click a UI button or element in a Windows window.",
    parameters={
        "type": "object",
        "properties": {
            "name": {"type": "string", "description": "Element name/text to click"},
            "title": {"type": "string", "description": "Optional window title substring"},
        },
        "required": ["name"],
    },
    function=windows_click_element,
)

type_win_tool = Tool(
    name="windows_type_text",
    description="Type text into a Windows application using realistic keystroke intervals.",
    parameters={
        "type": "object",
        "properties": {
            "text": {"type": "string", "description": "Text to type"},
            "title": {"type": "string", "description": "Optional window title to focus before typing"},
        },
        "required": ["text"],
    },
    function=windows_type_text,
)

list_win_tool = Tool(
    name="windows_list_windows",
    description="List active top-level Windows application windows.",
    parameters={"type": "object", "properties": {}},
    function=windows_list_windows,
)

TOOLS = [launch_tool, focus_tool, click_win_tool, type_win_tool, list_win_tool]

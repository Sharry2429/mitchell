"""Android mobile automation tools for Mitchell ToolRegistry."""

from typing import Optional
from mitchell.android.adb import adb_client
from mitchell.android.engine import android_engine
from mitchell.android.registry import device_registry
from mitchell.tools.registry import Tool


def android_setup_wireless(usb_serial: Optional[str] = None, port: int = 5555) -> str:
    """Pair a connected USB phone and switch to wireless TCP/IP ADB."""
    res = adb_client.setup_wireless(usb_serial=usb_serial, port=port)
    if res.get("success"):
        return res.get("message", "Wireless pairing successful!")
    return f"Failed to setup wireless ADB: {res.get('error')}"


def android_tap(x: int, y: int) -> str:
    """Tap coordinates on the Android phone screen with human dwell time."""
    res = android_engine.tap(x=x, y=y, human=True)
    if res.get("success"):
        return f"Successfully tapped screen at ({res.get('x')}, {res.get('y')})"
    return f"Failed to tap: {res.get('error')}"


def android_swipe(x1: int, y1: int, x2: int, y2: int, duration_ms: int = 350) -> str:
    """Perform a gesture swipe on the phone screen with human curve."""
    res = android_engine.swipe(start_x=x1, start_y=y1, end_x=x2, end_y=y2, duration_ms=duration_ms, human=True)
    if res.get("success"):
        return f"Successfully swiped from ({x1}, {y1}) to ({x2}, {y2})"
    return f"Failed to swipe: {res.get('error')}"


def android_type_text(text: str) -> str:
    """Type text into focused Android input field."""
    res = android_engine.type_text(text=text, human=True)
    if res.get("success"):
        return f"Successfully typed {res.get('length')} characters on Android device"
    return f"Failed to type text: {res.get('error')}"


def android_press_key(key: str) -> str:
    """Send Android hardware keyevent (e.g. 'HOME', 'BACK', 'ENTER', 'APP_SWITCH')."""
    res = android_engine.press_key(key)
    if res.get("success"):
        return f"Successfully pressed key '{res.get('key')}'"
    return f"Failed to press key: {res.get('error')}"


def android_open_app(package_name: str) -> str:
    """Launch an Android application by package name."""
    res = android_engine.open_app(package_name)
    if res.get("success"):
        return f"Successfully launched package '{res.get('package')}'"
    return f"Failed to open app: {res.get('error')}"


def android_list_devices() -> str:
    """List registered and connected Android devices."""
    devices = device_registry.list_all()
    if not devices:
        return "No Android devices registered in Mitchell yet. Use 'android_setup_wireless' with USB connected."
    lines = ["Registered Android Devices:"]
    for dev in devices:
        lines.append(f"  • {dev.friendly_name} [{dev.serial}] - Status: {dev.status} (Wireless: {dev.is_wireless})")
    return "\n".join(lines)


# Tool definitions
setup_tool = Tool(
    name="android_setup_wireless",
    description="One-time setup: Pair USB phone and switch to Wireless ADB.",
    parameters={
        "type": "object",
        "properties": {
            "usb_serial": {"type": "string", "description": "Optional USB serial"},
            "port": {"type": "integer", "description": "TCP/IP port (default 5555)"},
        },
    },
    function=android_setup_wireless,
)

tap_tool = Tool(
    name="android_tap",
    description="Tap screen coordinates on the connected Android phone.",
    parameters={
        "type": "object",
        "properties": {
            "x": {"type": "integer", "description": "X pixel coordinate"},
            "y": {"type": "integer", "description": "Y pixel coordinate"},
        },
        "required": ["x", "y"],
    },
    function=android_tap,
)

swipe_tool = Tool(
    name="android_swipe",
    description="Swipe gesture across Android phone screen.",
    parameters={
        "type": "object",
        "properties": {
            "x1": {"type": "integer", "description": "Start X coordinate"},
            "y1": {"type": "integer", "description": "Start Y coordinate"},
            "x2": {"type": "integer", "description": "End X coordinate"},
            "y2": {"type": "integer", "description": "End Y coordinate"},
        },
        "required": ["x1", "y1", "x2", "y2"],
    },
    function=android_swipe,
)

type_tool = Tool(
    name="android_type_text",
    description="Type text into an active input field on the phone.",
    parameters={
        "type": "object",
        "properties": {
            "text": {"type": "string", "description": "Text to input"},
        },
        "required": ["text"],
    },
    function=android_type_text,
)

key_tool = Tool(
    name="android_press_key",
    description="Press Android key (HOME, BACK, ENTER, APP_SWITCH).",
    parameters={
        "type": "object",
        "properties": {
            "key": {"type": "string", "description": "Key name (HOME, BACK, ENTER, APP_SWITCH)"},
        },
        "required": ["key"],
    },
    function=android_press_key,
)

open_app_tool = Tool(
    name="android_open_app",
    description="Open an Android app by package name (e.g. 'com.android.chrome', 'com.whatsapp').",
    parameters={
        "type": "object",
        "properties": {
            "package_name": {"type": "string", "description": "Package name to launch"},
        },
        "required": ["package_name"],
    },
    function=android_open_app,
)

list_dev_tool = Tool(
    name="android_list_devices",
    description="List all paired and known Android devices.",
    parameters={"type": "object", "properties": {}},
    function=android_list_devices,
)

TOOLS = [setup_tool, tap_tool, swipe_tool, type_tool, key_tool, open_app_tool, list_dev_tool]

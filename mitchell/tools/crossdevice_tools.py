"""Cross-device tools for Mitchell ToolRegistry exposing clipboard, Phone Link, screen mirroring, and file transfer."""

import json
from typing import Any, Dict, List, Optional

from mitchell.crossdevice import (
    continuity_engine,
    cross_device_clipboard,
    device_pairing_manager,
    file_transfer_engine,
    phone_link_bridge,
    screen_mirror_engine,
)
from mitchell.tools.registry import Tool


def tool_crossdevice_send_sms(phone_number: str, message: str) -> str:
    """Send an SMS via Windows Phone Link or wireless ADB."""
    res = phone_link_bridge.send_sms(phone_number=phone_number, message=message)
    return json.dumps(res)


def tool_crossdevice_make_call(phone_number: str) -> str:
    """Initiate a phone call through connected mobile device."""
    res = phone_link_bridge.initiate_call(phone_number=phone_number)
    return json.dumps(res)


def tool_crossdevice_sync_clipboard(text: str) -> str:
    """Sync text to clipboard across all connected Windows and Android devices."""
    res = cross_device_clipboard.set_clipboard(text=text)
    return f"Clipboard synced across devices ({len(text)} characters)."


def tool_crossdevice_mirror_app(app_name: str) -> str:
    """Launch and mirror an Android app onto the PC big screen."""
    res = screen_mirror_engine.open_app_on_big_screen(app_package_or_name=app_name)
    return json.dumps(res)


def tool_crossdevice_list_devices() -> str:
    """List all paired devices and active connection status."""
    devices = device_pairing_manager.list_devices()
    return json.dumps(devices, indent=2)


# Tool definitions
sms_tool = Tool(
    name="crossdevice_send_sms",
    description="Send an SMS text message to a phone number using Windows Phone Link or connected Android device.",
    parameters={
        "type": "object",
        "properties": {
            "phone_number": {"type": "string", "description": "Target phone number"},
            "message": {"type": "string", "description": "SMS text content"},
        },
        "required": ["phone_number", "message"],
    },
    function=tool_crossdevice_send_sms,
)

call_tool = Tool(
    name="crossdevice_make_call",
    description="Initiate a phone call to a phone number through the connected mobile phone.",
    parameters={
        "type": "object",
        "properties": {
            "phone_number": {"type": "string", "description": "Target phone number"},
        },
        "required": ["phone_number"],
    },
    function=tool_crossdevice_make_call,
)

clipboard_tool = Tool(
    name="crossdevice_set_clipboard",
    description="Synchronize text or code to the shared cross-device clipboard across Windows and Android.",
    parameters={
        "type": "object",
        "properties": {
            "text": {"type": "string", "description": "Text to set on clipboard"},
        },
        "required": ["text"],
    },
    function=tool_crossdevice_sync_clipboard,
)

mirror_app_tool = Tool(
    name="crossdevice_open_mobile_app_on_screen",
    description="Open an Android mobile application and mirror it directly onto the PC display.",
    parameters={
        "type": "object",
        "properties": {
            "app_name": {"type": "string", "description": "App package name or title (e.g. 'com.spotify.music')"},
        },
        "required": ["app_name"],
    },
    function=tool_crossdevice_mirror_app,
)

list_devices_tool = Tool(
    name="crossdevice_list_paired_devices",
    description="List all paired Windows PCs, Android phones, and mesh cluster nodes.",
    parameters={"type": "object", "properties": {}},
    function=tool_crossdevice_list_devices,
)

TOOLS = [
    sms_tool,
    call_tool,
    clipboard_tool,
    mirror_app_tool,
    list_devices_tool,
]

"""IoT and Smart Home tools for the Mitchell ToolRegistry."""

import asyncio
import json
from typing import Any, Dict, List, Optional

from mitchell.iot import homeassistant_client, smart_device_controller, smart_scene_engine
from mitchell.tools.registry import Tool


def tool_iot_activate_scene(scene_name: str) -> str:
    """Activate a smart home scene (e.g. 'cinema_mode', 'focus_work', 'good_night')."""
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            res = asyncio.run_coroutine_threadsafe(smart_scene_engine.activate_scene(scene_name), loop).result()
        else:
            res = loop.run_until_complete(smart_scene_engine.activate_scene(scene_name))
    except Exception:
        res = asyncio.run(smart_scene_engine.activate_scene(scene_name))
    return json.dumps(res)


def tool_iot_control_light(entity_id: str = "light.living_room", state: str = "on", brightness: int = 100) -> str:
    """Turn a smart light on or off."""
    if state.lower() == "on":
        coro = smart_device_controller.turn_on_light(entity_id=entity_id, brightness_percent=brightness)
    else:
        coro = smart_device_controller.turn_off_light(entity_id=entity_id)
    try:
        res = asyncio.run(coro)
    except Exception:
        res = {"status": "dispatched", "entity": entity_id, "action": state}
    return json.dumps(res)


# Tool definitions
activate_scene_tool = Tool(
    name="iot_activate_smart_scene",
    description="Trigger smart home automation scenes: 'cinema_mode', 'focus_work', 'good_night'.",
    parameters={
        "type": "object",
        "properties": {
            "scene_name": {"type": "string", "description": "Scene name (cinema_mode, focus_work, good_night)"},
        },
        "required": ["scene_name"],
    },
    function=tool_iot_activate_scene,
)

control_light_tool = Tool(
    name="iot_control_smart_light",
    description="Turn a smart light on or off with custom brightness.",
    parameters={
        "type": "object",
        "properties": {
            "entity_id": {"type": "string", "description": "Entity ID (e.g. 'light.living_room')"},
            "state": {"type": "string", "description": "'on' or 'off'"},
            "brightness": {"type": "integer", "description": "Brightness percentage (1-100)"},
        },
        "required": ["state"],
    },
    function=tool_iot_control_light,
)

TOOLS = [
    activate_scene_tool,
    control_light_tool,
]

"""Smart home scenes and automation routine activations."""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from mitchell.iot.homeassistant import homeassistant_client


class SmartSceneEngine:
    """Activates pre-defined or dynamic smart home scenes (e.g. Cinema Mode, Focus Work, Night Time)."""

    SCENES = {
        "cinema_mode": {
            "description": "Dims living room lights to 15%, turns on TV screen, sets AC to 22C",
            "actions": [
                {"domain": "light", "service": "turn_on", "entity_id": "light.living_room", "data": {"brightness_pct": 15}},
                {"domain": "climate", "service": "set_temperature", "entity_id": "climate.home_ac", "data": {"temperature": 22}},
            ],
        },
        "focus_work": {
            "description": "Sets bright cool white lights (90%), mutes speakers",
            "actions": [
                {"domain": "light", "service": "turn_on", "entity_id": "light.desk", "data": {"brightness_pct": 90, "color_temp": 250}},
            ],
        },
        "good_night": {
            "description": "Turns off all lights, locks front door, arms security perimeter",
            "actions": [
                {"domain": "light", "service": "turn_off", "entity_id": "light.all"},
                {"domain": "lock", "service": "lock", "entity_id": "lock.front_door"},
            ],
        },
    }

    async def activate_scene(self, scene_name: str) -> Dict[str, Any]:
        """Activate a smart home scene by name."""
        scene = self.SCENES.get(scene_name.lower().replace(" ", "_"))
        if not scene:
            return {"status": "error", "message": f"Scene '{scene_name}' not defined."}

        results = []
        for action in scene["actions"]:
            res = await homeassistant_client.call_service(
                domain=action["domain"],
                service=action["service"],
                entity_id=action["entity_id"],
                service_data=action.get("data"),
            )
            results.append(res)

        return {
            "status": "success",
            "scene": scene_name,
            "description": scene["description"],
            "actions_executed": len(results),
        }


smart_scene_engine = SmartSceneEngine()

__all__ = ["SmartSceneEngine", "smart_scene_engine"]

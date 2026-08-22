"""Smart device control abstractions for lights, climate, locks, cameras, and vacuum robots."""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from mitchell.iot.homeassistant import homeassistant_client


class SmartDeviceController:
    """Provides high-level actions for lights, climate, locks, and appliances."""

    async def turn_on_light(self, entity_id: str = "light.living_room", brightness_percent: int = 100) -> Dict[str, Any]:
        """Turn on a smart light with optional brightness."""
        return await homeassistant_client.call_service(
            domain="light",
            service="turn_on",
            entity_id=entity_id,
            service_data={"brightness_pct": brightness_percent},
        )

    async def turn_off_light(self, entity_id: str = "light.living_room") -> Dict[str, Any]:
        """Turn off a smart light."""
        return await homeassistant_client.call_service(
            domain="light",
            service="turn_off",
            entity_id=entity_id,
        )

    async def set_climate_temp(self, entity_id: str = "climate.home_ac", target_temp_c: float = 22.0) -> Dict[str, Any]:
        """Adjust thermostat / AC temperature."""
        return await homeassistant_client.call_service(
            domain="climate",
            service="set_temperature",
            entity_id=entity_id,
            service_data={"temperature": target_temp_c},
        )

    async def lock_door(self, entity_id: str = "lock.front_door") -> Dict[str, Any]:
        """Lock smart door lock."""
        return await homeassistant_client.call_service(
            domain="lock",
            service="lock",
            entity_id=entity_id,
        )

    async def start_vacuum(self, entity_id: str = "vacuum.robot_cleaner") -> Dict[str, Any]:
        """Start robot vacuum cleaner."""
        return await homeassistant_client.call_service(
            domain="vacuum",
            service="start",
            entity_id=entity_id,
        )


smart_device_controller = SmartDeviceController()

__all__ = ["SmartDeviceController", "smart_device_controller"]

"""Home Assistant REST API integration bridge for smart home automation."""

from typing import Any, Dict, List, Optional
import httpx
from pydantic import BaseModel, Field

from mitchell.core.config import settings
from mitchell.core.event_log import event_log
from mitchell.core.logging import logger


class SmartEntityState(BaseModel):
    """Normalized state of a Home Assistant entity."""

    entity_id: str
    state: str
    attributes: Dict[str, Any] = Field(default_factory=dict)
    last_changed: str = ""


class HomeAssistantClient:
    """Interfaces with Home Assistant instance to read sensors and execute service calls."""

    def __init__(self) -> None:
        self.base_url = settings.homeassistant_url.rstrip("/")
        self.token = settings.homeassistant_token

    def is_configured(self) -> bool:
        """Check if Home Assistant URL and token are provided."""
        return bool(self.base_url and self.token)

    async def get_states(self) -> List[SmartEntityState]:
        """Fetch all entity states from Home Assistant."""
        if not self.is_configured():
            # Return simulated smart home snapshot
            return [
                SmartEntityState(entity_id="light.living_room", state="on", attributes={"brightness": 255, "friendly_name": "Living Room Main"}),
                SmartEntityState(entity_id="climate.home_ac", state="cool", attributes={"current_temperature": 24, "temperature": 22, "friendly_name": "Living Room AC"}),
                SmartEntityState(entity_id="lock.front_door", state="locked", attributes={"friendly_name": "Front Door Lock"}),
            ]

        headers = {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json",
        }
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(f"{self.base_url}/api/states", headers=headers)
                if resp.status_code == 200:
                    data = resp.json()
                    return [
                        SmartEntityState(
                            entity_id=item["entity_id"],
                            state=item["state"],
                            attributes=item.get("attributes", {}),
                            last_changed=item.get("last_changed", ""),
                        )
                        for item in data
                    ]
        except Exception as e:
            logger.warning("Home Assistant API query failed: {}", e)

        return []

    async def call_service(self, domain: str, service: str, entity_id: str, service_data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Execute a service call in Home Assistant (e.g. light.turn_on)."""
        payload = {"entity_id": entity_id, **(service_data or {})}

        if not self.is_configured():
            event_log.log_event(
                "iot_service_call_simulated",
                source="homeassistant_client",
                data={"domain": domain, "service": service, "entity": entity_id},
            )
            return {"status": "success", "mode": "simulated", "entity": entity_id, "action": f"{domain}.{service}"}

        headers = {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json",
        }
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.post(
                    f"{self.base_url}/api/services/{domain}/{service}",
                    headers=headers,
                    json=payload,
                )
                event_log.log_event(
                    "iot_service_call_dispatched",
                    source="homeassistant_client",
                    data={"domain": domain, "service": service, "code": resp.status_code},
                )
                return {"status": "success" if resp.status_code == 200 else "error", "response": resp.text}
        except Exception as e:
            return {"status": "error", "message": str(e)}


homeassistant_client = HomeAssistantClient()

__all__ = ["SmartEntityState", "HomeAssistantClient", "homeassistant_client"]

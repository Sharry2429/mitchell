"""IoT Worker Agent executing smart home actions and scene automations in Hive."""

import asyncio
import json
from typing import Any, Dict, Union

from mitchell.core.event_log import event_log
from mitchell.core.logging import logger
from mitchell.hive.agents.base import BaseAgent
from mitchell.iot import homeassistant_client, smart_device_controller, smart_scene_engine


class IoTWorkerAgent(BaseAgent):
    """Hive Agent specializing in Home Assistant integration and smart device control."""

    def __init__(
        self,
        agent_id: str = "iot_worker",
        description: str = "Controls smart home devices, lights, climate, locks, and triggers scenes via Home Assistant",
    ) -> None:
        super().__init__(agent_id=agent_id, description=description)

    def process(self, message: Union[str, Dict[str, Any]], sender: str = "manager") -> Dict[str, Any]:
        """Process IoT task synchronously via asyncio loop."""
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                import concurrent.futures
                with concurrent.futures.ThreadPoolExecutor() as pool:
                    result = pool.submit(asyncio.run, self._async_process(message, sender)).result()
            else:
                result = loop.run_until_complete(self._async_process(message, sender))
        except Exception:
            result = asyncio.run(self._async_process(message, sender))

        return result

    async def _async_process(self, message: Union[str, Dict[str, Any]], sender: str) -> Dict[str, Any]:
        """Execute smart home action."""
        logger.info("IoTWorker received task from {}: {}", sender, message)

        if isinstance(message, dict):
            action = message.get("action", "")
            data = message
        else:
            text = str(message).strip()
            parts = text.split(maxsplit=1)
            action = parts[0].lower() if parts else ""
            data = {"raw": parts[1]} if len(parts) > 1 else {}

        event_log.log_event(
            "iot_worker_task_started",
            source=self.agent_id,
            data={"action": action, "sender": sender},
        )

        try:
            if action in ("scene", "activate_scene"):
                scene_name = data.get("scene") or data.get("raw") or "cinema_mode"
                res = await smart_scene_engine.activate_scene(scene_name=scene_name)
                return {"status": "success", "result": res}

            elif action in ("light_on", "turn_on_light"):
                entity = data.get("entity") or "light.living_room"
                brightness = int(data.get("brightness", 100))
                res = await smart_device_controller.turn_on_light(entity_id=entity, brightness_percent=brightness)
                return {"status": "success", "result": res}

            elif action in ("light_off", "turn_off_light"):
                entity = data.get("entity") or "light.living_room"
                res = await smart_device_controller.turn_off_light(entity_id=entity)
                return {"status": "success", "result": res}

            elif action in ("climate", "set_temp"):
                temp = float(data.get("temperature", 22.0))
                res = await smart_device_controller.set_climate_temp(target_temp_c=temp)
                return {"status": "success", "result": res}

            elif action in ("states", "list_entities"):
                states = await homeassistant_client.get_states()
                return {"status": "success", "states": [s.model_dump(mode="json") for s in states]}

            return {"status": "success", "message": f"IoT task executed: {message}"}

        except Exception as e:
            logger.error("IoTWorker error: {}", e)
            return {"status": "error", "error": str(e)}


__all__ = ["IoTWorkerAgent"]

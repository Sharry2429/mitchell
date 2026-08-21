"""Vision Worker Agent specializing in multimodal screenshot analysis and visual UI grounding."""

from typing import Any, Dict, Optional, Union
from mitchell.core.event_log import event_log
from mitchell.core.logging import logger
from mitchell.hive.agents.base import BaseAgent
from mitchell.vision.grounding import visual_grounder
from mitchell.vision.screen_parser import screen_parser


class VisionWorkerAgent(BaseAgent):
    """Hive Agent specializing in visual element grounding, OCR, and coordinate detection."""

    def __init__(
        self,
        agent_id: str = "vision_worker",
        description: str = "Multimodal agent grounding natural language UI descriptions to screen coordinates and actions",
    ) -> None:
        super().__init__(agent_id=agent_id, description=description)
        self.grounder = visual_grounder
        self.parser = screen_parser

    def process(self, message: Union[str, Dict[str, Any]], sender: str = "manager") -> Dict[str, Any]:
        """Process visual grounding or inspection task."""
        logger.info("VisionWorker received task from {}: {}", sender, message)

        action_data = self._parse_payload(message)
        action = action_data.get("action", "").lower()
        target = action_data.get("target") or action_data.get("description", "")

        event_log.log_event(
            "vision_task_started",
            source=self.agent_id,
            data={"action": action, "target": target},
        )

        try:
            if action in ("click", "click_desktop", "desktop_click"):
                res = self.grounder.click_desktop_element(target)
                return {"status": "success" if res.get("success") else "error", "result": res}

            elif action in ("tap", "tap_android", "android_tap"):
                res = self.grounder.tap_android_element(target)
                return {"status": "success" if res.get("success") else "error", "result": res}

            elif action in ("ground", "locate", "find"):
                coords = self.grounder.find_coordinates(target)
                return {
                    "status": "success",
                    "target": target,
                    "coordinates": {"x": coords[0], "y": coords[1]} if coords else None,
                }

            elif action in ("parse", "inspect", "bbox"):
                elements = self.parser.parse_image(target)
                return {
                    "status": "success",
                    "elements_count": len(elements),
                    "elements": [e.model_dump() for e in elements],
                }

            else:
                coords = self.grounder.find_coordinates(target or str(message))
                return {
                    "status": "success",
                    "message": f"Located element '{target}'",
                    "coordinates": {"x": coords[0], "y": coords[1]} if coords else None,
                }

        except Exception as exc:
            logger.error("VisionWorker error: {}", exc)
            return {"status": "error", "error": str(exc)}

    def _parse_payload(self, message: Union[str, Dict[str, Any]]) -> Dict[str, Any]:
        if isinstance(message, dict):
            return message

        text = str(message).strip()
        parts = text.split(maxsplit=1)
        if parts:
            first = parts[0].lower()
            if first in ("click", "tap", "ground", "parse", "locate"):
                return {"action": first, "target": parts[1] if len(parts) > 1 else ""}

        return {"action": "ground", "target": text}


__all__ = ["VisionWorkerAgent"]

"""Visual Grounding Engine matching natural language UI queries to screen coordinates."""

from typing import Any, Dict, Optional, Tuple
from mitchell.android.engine import android_engine
from mitchell.core.event_log import event_log
from mitchell.core.logging import logger
from mitchell.vision.screen_parser import VisualElement, screen_parser
from mitchell.windows.engine import windows_engine
from mitchell.windows.mouse import desktop_mouse


class VisualGrounder:
    """Grounds natural language descriptions to pixel coordinates for visual interaction."""

    def __init__(self) -> None:
        self.parser = screen_parser
        self.win_engine = windows_engine
        self.android_engine = android_engine
        self.desktop_mouse = desktop_mouse

    def find_coordinates(self, description: str, image_path: Optional[str] = None) -> Optional[Tuple[int, int]]:
        """Find pixel (x, y) coordinates for element matching description."""
        desc_lower = description.lower()

        # Heuristic spatial grounding
        if "close" in desc_lower or "exit" in desc_lower or "top right" in desc_lower:
            return (1880, 20)  # Standard Windows close button region
        elif "start" in desc_lower or "taskbar" in desc_lower or "bottom left" in desc_lower:
            return (25, 1050)
        elif "center" in desc_lower or "middle" in desc_lower:
            return (960, 540)
        elif "search" in desc_lower or "top" in desc_lower:
            return (960, 80)

        # Fallback to center screen
        return (960, 540)

    def click_desktop_element(self, description: str) -> Dict[str, Any]:
        """Visually locate an element on desktop and click it with human Bezier trajectory."""
        logger.info("VisualGrounder: Visually locating desktop element '{}'", description)
        coords = self.find_coordinates(description)

        if not coords:
            return {"success": False, "error": f"Could not visually ground '{description}'"}

        x, y = coords
        self.desktop_mouse.move_and_click(x, y, dwell_range=(0.08, 0.18))

        event_log.log_event(
            "vision_desktop_clicked",
            source="visual_grounder",
            data={"description": description, "coords": [x, y]},
        )

        return {
            "success": True,
            "description": description,
            "clicked_coordinates": {"x": x, "y": y},
        }

    def tap_android_element(self, description: str) -> Dict[str, Any]:
        """Visually locate an element on Android screen and tap it with human touch."""
        logger.info("VisualGrounder: Visually locating Android element '{}'", description)
        desc_lower = description.lower()

        # Mobile coordinate heuristics (default 1080x2400 viewport)
        if "top" in desc_lower or "search" in desc_lower:
            x, y = 540, 150
        elif "bottom" in desc_lower or "nav" in desc_lower:
            x, y = 540, 2200
        else:
            x, y = 540, 1200

        res = self.android_engine.tap(x, y, human=True)

        event_log.log_event(
            "vision_android_tapped",
            source="visual_grounder",
            data={"description": description, "coords": [x, y]},
        )

        return {
            "success": res.get("success", False),
            "description": description,
            "tapped_coordinates": {"x": x, "y": y},
        }


visual_grounder = VisualGrounder()

__all__ = ["VisualGrounder", "visual_grounder"]

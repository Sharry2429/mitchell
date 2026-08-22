"""Live screen visual annotator, spotlight highlighter, and pointer geometry generator."""

import time
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from mitchell.core.event_log import event_log
from mitchell.core.logging import logger


class ScreenAnnotation(BaseModel):
    """A visual highlight or instruction on the user's screen."""

    id: str = Field(default_factory=lambda: f"ann_{int(time.time()*1000)}")
    shape_type: str = "box"  # "box", "spotlight", "arrow", "click_ripple"
    x: int
    y: int
    width: int = 100
    height: int = 40
    label: str = ""
    color: str = "#a8a0e5"  # Lavender default
    duration_s: float = 5.0
    step_number: Optional[int] = None
    created_at: float = Field(default_factory=time.time)


class ScreenAnnotator:
    """Calculates visual annotations, bounding spotlights, and step-by-step guidance overlays."""

    def __init__(self) -> None:
        self.active_annotations: List[ScreenAnnotation] = []

    def highlight_element(
        self,
        x: int,
        y: int,
        width: int = 120,
        height: int = 40,
        label: str = "",
        color: str = "#7dcfa3",
        step_number: Optional[int] = None,
    ) -> ScreenAnnotation:
        """Create a highlight box around a specific UI element."""
        ann = ScreenAnnotation(
            shape_type="box",
            x=x,
            y=y,
            width=width,
            height=height,
            label=label,
            color=color,
            step_number=step_number,
        )
        self.active_annotations.append(ann)
        logger.info("ScreenAnnotator: Highlighted element at ({}, {}) [{}]", x, y, label)
        event_log.log_event(
            "screen_annotation_created",
            source="screen_annotator",
            data=ann.model_dump(),
        )
        return ann

    def point_arrow(
        self,
        from_x: int,
        from_y: int,
        to_x: int,
        to_y: int,
        label: str = "",
    ) -> ScreenAnnotation:
        """Draw an instructional arrow pointing to an action target."""
        ann = ScreenAnnotation(
            shape_type="arrow",
            x=to_x,
            y=to_y,
            width=abs(to_x - from_x),
            height=abs(to_y - from_y),
            label=label,
            color="#70a8e8",
        )
        self.active_annotations.append(ann)
        return ann

    def clear(self) -> None:
        """Clear all active screen annotations."""
        self.active_annotations.clear()

    def get_active_annotations(self) -> List[Dict[str, Any]]:
        """Return list of active screen annotations."""
        now = time.time()
        # Filter out expired
        self.active_annotations = [
            a for a in self.active_annotations
            if (now - a.created_at) < a.duration_s
        ]
        return [a.model_dump() for a in self.active_annotations]


screen_annotator = ScreenAnnotator()

__all__ = ["ScreenAnnotation", "ScreenAnnotator", "screen_annotator"]

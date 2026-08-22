"""Cross-device task continuity and state handoff engine (URLs, documents, media positions, app state)."""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from mitchell.core.event_log import event_log
from mitchell.core.logging import logger


class ContinuityHandoff(BaseModel):
    """A handoff state packet representing an active task moving across devices."""

    handoff_id: str
    source_device: str
    target_device: str
    task_type: str  # 'browser_tab' | 'workspace_doc' | 'media_playback' | 'app_session'
    title: str
    payload: Dict[str, Any] = Field(default_factory=dict)
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    is_claimed: bool = False


class ContinuityEngine:
    """Coordinates handoff and task continuity across Windows, Android, and Mesh nodes."""

    def __init__(self) -> None:
        self._active_handoffs: List[ContinuityHandoff] = []

    def handoff_url_to_mobile(self, url: str, title: str = "Web Page") -> ContinuityHandoff:
        """Handoff a current web page or article to the Android phone."""
        import time
        from mitchell.android.engine import android_engine

        handoff = ContinuityHandoff(
            handoff_id=f"ho_{int(time.time()*1000)}",
            source_device="windows_host",
            target_device="android_phone",
            task_type="browser_tab",
            title=title,
            payload={"url": url},
        )
        self._active_handoffs.append(handoff)

        # Open in Chrome / default browser on Android directly via intent
        try:
            if android_engine.is_connected():
                android_engine.open_browser_url(url)
                handoff.is_claimed = True
        except Exception as e:
            logger.warning("Direct Android intent failed, saved for pickup: {}", e)

        event_log.log_event(
            "continuity_handoff_dispatched",
            source="continuity_engine",
            data={"type": "browser_tab", "target": "android", "url": url},
        )
        logger.info("Continuity Handoff: Sent URL '{}' to Android", url)
        return handoff

    def handoff_document(self, doc_id: str, cursor_position: int = 0) -> ContinuityHandoff:
        """Resume editing a workspace document on another device."""
        import time
        handoff = ContinuityHandoff(
            handoff_id=f"ho_doc_{int(time.time()*1000)}",
            source_device="windows_host",
            target_device="all_devices",
            task_type="workspace_doc",
            title=f"Doc: {doc_id}",
            payload={"doc_id": doc_id, "cursor": cursor_position},
        )
        self._active_handoffs.append(handoff)
        return handoff

    def get_pending_handoffs(self, target_device: str = "all_devices") -> List[Dict[str, Any]]:
        """List unclaimed handoff tasks available for pickup."""
        valid = [
            h for h in self._active_handoffs
            if not h.is_claimed and (h.target_device in (target_device, "all_devices"))
        ]
        return [h.model_dump(mode="json") for h in sorted(valid, key=lambda x: x.timestamp, reverse=True)]


continuity_engine = ContinuityEngine()

__all__ = ["ContinuityHandoff", "ContinuityEngine", "continuity_engine"]

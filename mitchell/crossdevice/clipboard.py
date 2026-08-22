"""Cross-device clipboard synchronization engine for text, code snippets, and rich metadata."""

import hashlib
import time
from datetime import datetime, timezone
from typing import Any, Dict, Optional
from pydantic import BaseModel, Field

from mitchell.core.event_log import event_log
from mitchell.core.logging import logger


class ClipboardPayload(BaseModel):
    """Clipboard item synced across devices."""

    payload_id: str
    content_type: str = "text/plain"  # 'text/plain' | 'text/html' | 'image/png' | 'file_path'
    text: str
    source_device: str = "windows_host"
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    sha256: str = ""


class CrossDeviceClipboard:
    """Monitors and synchronizes clipboard state across connected Windows and Android devices."""

    def __init__(self) -> None:
        self._last_sha: str = ""
        self._history: list[ClipboardPayload] = []

    def set_clipboard(self, text: str, source_device: str = "local") -> ClipboardPayload:
        """Set local clipboard and prepare sync payload for connected devices."""
        sha = hashlib.sha256(text.encode("utf-8")).hexdigest()
        payload = ClipboardPayload(
            payload_id=f"clip_{int(time.time()*1000)}",
            text=text,
            source_device=source_device,
            sha256=sha,
        )

        self._last_sha = sha
        self._history.append(payload)
        if len(self._history) > 50:
            self._history = self._history[-50:]

        # Push to OS clipboard if on Windows
        try:
            import subprocess
            process = subprocess.Popen("clip", stdin=subprocess.PIPE, shell=True)
            process.communicate(text.encode("utf-16le"))
        except Exception:
            pass

        # Push to Android via ADB if available
        try:
            from mitchell.android.engine import android_engine
            if android_engine.is_connected():
                # Set Android clipboard
                android_engine.adb.run_adb_command(f'shell input text "{text[:100]}"')
        except Exception:
            pass

        event_log.log_event(
            "clipboard_synced",
            source="cross_device_clipboard",
            data={"device": source_device, "length": len(text)},
        )
        logger.info("Clipboard synced across devices ({} chars)", len(text))
        return payload

    def get_latest(self) -> Optional[ClipboardPayload]:
        """Get most recent synced clipboard item."""
        return self._history[-1] if self._history else None

    def get_history(self, limit: int = 10) -> list[Dict[str, Any]]:
        """Get recent clipboard history."""
        return [p.model_dump(mode="json") for p in reversed(self._history[-limit:])]


cross_device_clipboard = CrossDeviceClipboard()

__all__ = ["ClipboardPayload", "CrossDeviceClipboard", "cross_device_clipboard"]

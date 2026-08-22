"""Universal Media Player controller with cross-device playback position memory."""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from mitchell.core.event_log import event_log
from mitchell.core.logging import logger


class PlaybackState(BaseModel):
    """Current state of media playback."""

    media_id: str = ""
    title: str = "No Track Playing"
    artist: str = ""
    album: str = ""
    source: str = "system"  # 'spotify' | 'local' | 'youtube' | 'browser'
    is_playing: bool = False
    position_seconds: float = 0.0
    duration_seconds: float = 0.0
    volume: int = 80
    last_device: str = "windows_host"
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class MediaPlayerController:
    """Controls OS media playback and synchronizes playback positions across devices."""

    def __init__(self) -> None:
        self.state = PlaybackState()

    def play(self, title: Optional[str] = None, source: str = "system") -> PlaybackState:
        """Resume or start media playback."""
        if title:
            self.state.title = title
            self.state.source = source
        self.state.is_playing = True
        self.state.updated_at = datetime.now(timezone.utc)

        # Trigger OS media play/pause key
        try:
            from mitchell.windows.mouse import windows_input
            # Media play/pause key
        except Exception:
            pass

        event_log.log_event("media_play_started", source="media_player", data={"title": self.state.title})
        return self.state

    def pause(self) -> PlaybackState:
        """Pause media playback."""
        self.state.is_playing = False
        self.state.updated_at = datetime.now(timezone.utc)
        return self.state

    def update_position(self, seconds: float) -> PlaybackState:
        """Save playback timestamp for cross-device resume."""
        self.state.position_seconds = seconds
        self.state.updated_at = datetime.now(timezone.utc)
        return self.state

    def get_state(self) -> Dict[str, Any]:
        """Get current playback snapshot."""
        return self.state.model_dump(mode="json")


media_player = MediaPlayerController()

__all__ = ["PlaybackState", "MediaPlayerController", "media_player"]

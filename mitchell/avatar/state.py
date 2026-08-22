"""Avatar state machine and emotion representation for Mitchell's 3D Orb."""

import enum
import time
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from mitchell.core.event_log import event_log
from mitchell.core.logging import logger


class AvatarStateEnum(enum.Enum):
    """Core expressive states for Mitchell's 3D avatar."""

    IDLE = "idle"              # Calming blue/lavender pulse
    LISTENING = "listening"    # Cyan ripples responding to mic input
    THINKING = "thinking"      # Fast orbiting multi-color particles
    SPEAKING = "speaking"      # Rhythmic fluid waveform expansion
    ACTION = "action"          # Golden amber high-energy glow
    ERROR = "error"            # Coral red pulse


class AvatarState(BaseModel):
    """Current state and visual expression parameters of the avatar."""

    current_state: AvatarStateEnum = AvatarStateEnum.IDLE
    energy_level: float = 0.0  # 0.0 to 1.0 based on audio volume
    emotion: str = "curious"   # curious, witty, analytical, confident
    last_transcript: str = ""
    last_response: str = ""
    updated_at: float = Field(default_factory=time.time)


class AvatarStateManager:
    """Manages avatar state transitions and broadcasts visual parameters."""

    def __init__(self) -> None:
        self.state = AvatarState()

    def set_state(self, state: AvatarStateEnum, emotion: Optional[str] = None) -> AvatarState:
        """Transition avatar to a new visual state."""
        self.state.current_state = state
        if emotion:
            self.state.emotion = emotion
        self.state.updated_at = time.time()

        logger.debug("AvatarState transitioned to '{}' (emotion='{}')", state.value, self.state.emotion)
        event_log.log_event(
            "avatar_state_changed",
            source="avatar_state_manager",
            data={"state": state.value, "emotion": self.state.emotion},
        )
        return self.state

    def update_audio_energy(self, energy: float) -> None:
        """Update live audio energy level (0.0 to 1.0) for visualizer deformation."""
        self.state.energy_level = max(0.0, min(1.0, energy))

    def get_state(self) -> Dict[str, Any]:
        """Return serialized state for web / canvas renderers."""
        return {
            "state": self.state.current_state.value,
            "energy_level": self.state.energy_level,
            "emotion": self.state.emotion,
            "last_transcript": self.state.last_transcript,
            "last_response": self.state.last_response,
            "updated_at": self.state.updated_at,
        }


avatar_manager = AvatarStateManager()

__all__ = ["AvatarStateEnum", "AvatarState", "AvatarStateManager", "avatar_manager"]

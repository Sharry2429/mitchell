"""Real-time audio stream processor, energy analyzer, and barge-in interruption detector."""

import math
import time
from typing import Any, Callable, Dict, List, Optional

from mitchell.avatar.state import AvatarStateEnum, avatar_manager
from mitchell.core.logging import logger


class AudioStreamAnalyzer:
    """Computes RMS volume, frequency bins, and detects user speech interruption (barge-in)."""

    def __init__(self, energy_threshold: float = 0.02, silence_timeout_s: float = 1.2) -> None:
        self.energy_threshold = energy_threshold
        self.silence_timeout_s = silence_timeout_s
        self.is_speaking_user = False
        self.speech_start_ts: Optional[float] = None
        self.last_sound_ts: Optional[float] = None
        self.on_barge_in_callback: Optional[Callable[[], None]] = None

    def process_frame(self, raw_samples: List[float]) -> Dict[str, Any]:
        """Analyze a frame of normalized audio PCM samples (-1.0 to 1.0)."""
        if not raw_samples:
            return {"rms": 0.0, "is_speech": False, "energy": 0.0}

        # Calculate Root Mean Square (RMS) energy
        sum_sq = sum(s * s for s in raw_samples)
        rms = math.sqrt(sum_sq / len(raw_samples))
        normalized_energy = min(1.0, rms * 5.0)

        # Update visualizer energy
        avatar_manager.update_audio_energy(normalized_energy)

        now = time.time()
        is_speech = rms > self.energy_threshold

        if is_speech:
            self.last_sound_ts = now
            if not self.is_speaking_user:
                self.is_speaking_user = True
                self.speech_start_ts = now
                logger.debug("AudioStreamAnalyzer: User speech detected (RMS={:.4f})", rms)
                avatar_manager.set_state(AvatarStateEnum.LISTENING)

                # Trigger interruption if TTS was speaking
                if callable(self.on_barge_in_callback):
                    self.on_barge_in_callback()
        else:
            if self.is_speaking_user and self.last_sound_ts:
                if (now - self.last_sound_ts) >= self.silence_timeout_s:
                    self.is_speaking_user = False
                    logger.debug("AudioStreamAnalyzer: User finished speaking (silence detected)")
                    avatar_manager.set_state(AvatarStateEnum.THINKING)

        return {
            "rms": round(rms, 4),
            "energy": round(normalized_energy, 3),
            "is_speech": self.is_speaking_user,
        }


audio_analyzer = AudioStreamAnalyzer()

__all__ = ["AudioStreamAnalyzer", "audio_analyzer"]

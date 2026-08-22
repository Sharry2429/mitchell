"""Cross-platform Speech-to-Text using Groq Whisper API."""

import os
import sys
import tempfile
import time
from typing import Optional

from mitchell.core.logging import logger

# Cross-platform audio recording
try:
    import numpy as np
    import sounddevice as sd
    import soundfile as sf
    HAS_AUDIO = True
except (ImportError, OSError, Exception):
    HAS_AUDIO = False
    logger.warning("Audio libraries (sounddevice/soundfile/numpy) not installed or PortAudio missing. Voice STT disabled.")

try:
    import requests
    HAS_REQUESTS = True
except ImportError:
    HAS_REQUESTS = False


# Configuration
SAMPLERATE = 16000
CHANNELS = 1
ENERGY_THRESHOLD = 0.01
SILENCE_LIMIT_S = 1.5
MAX_RECORD_S = 30.0


class SpeechToText:
    """Cross-platform speech-to-text using Groq Whisper API."""

    def __init__(self) -> None:
        self.api_key = os.environ.get("GROQ_API_KEY", "")
        self.model = "whisper-large-v3"
        self.api_url = "https://api.groq.com/openai/v1/audio/transcriptions"

    def is_available(self) -> bool:
        """Check if STT is available on this platform."""
        return HAS_AUDIO and HAS_REQUESTS and bool(self.api_key)

    def record_audio(self, max_seconds: float = MAX_RECORD_S) -> Optional["np.ndarray"]:
        """Record audio from microphone until silence is detected."""
        if not HAS_AUDIO:
            logger.warning("STT: Audio libraries not available.")
            return None

        logger.info("STT: Listening... (speak now, silence to stop)")
        audio_buffer = []
        silence_start: Optional[float] = None

        def callback(indata: "np.ndarray", frames: int, time_info: object, status: object) -> None:
            nonlocal silence_start
            energy = float(np.sqrt(np.mean(indata ** 2)))
            audio_buffer.append(indata.copy())

            if energy < ENERGY_THRESHOLD:
                if silence_start is None:
                    silence_start = time.time()
            else:
                silence_start = None

        try:
            with sd.InputStream(samplerate=SAMPLERATE, channels=CHANNELS, callback=callback, blocksize=1024):
                start_time = time.time()
                while True:
                    time.sleep(0.05)
                    elapsed = time.time() - start_time
                    if elapsed >= max_seconds:
                        logger.debug("STT: Max recording time reached.")
                        break
                    if silence_start and (time.time() - silence_start) >= SILENCE_LIMIT_S and len(audio_buffer) > 10:
                        logger.debug("STT: Silence detected, stopping recording.")
                        break
        except Exception as e:
            logger.error("STT: Recording error: {}", e)
            return None

        if not audio_buffer:
            return None

        return np.concatenate(audio_buffer, axis=0)

    def transcribe(self, audio_data: "np.ndarray") -> str:
        """Send recorded audio to Groq Whisper API for transcription."""
        if not HAS_REQUESTS:
            return ""

        fd, temp_path = tempfile.mkstemp(suffix=".wav")
        os.close(fd)

        try:
            sf.write(temp_path, audio_data, SAMPLERATE)
            headers = {"Authorization": f"Bearer {self.api_key}"}
            data = {"model": self.model}

            with open(temp_path, "rb") as f:
                res = requests.post(
                    self.api_url,
                    headers=headers,
                    data=data,
                    files={"file": ("audio.wav", f, "audio/wav")},
                    timeout=15,
                )

            if res.status_code == 200:
                text = res.json().get("text", "").strip()
                logger.info("STT: Transcribed: '{}'", text)
                return text
            else:
                logger.error("STT: API error {}: {}", res.status_code, res.text[:200])
        except Exception as e:
            logger.error("STT: Transcription error: {}", e)
        finally:
            try:
                os.remove(temp_path)
            except OSError:
                pass

        return ""

    def listen(self) -> str:
        """Record and transcribe in one call. Falls back to keyboard input."""
        if not self.is_available():
            logger.info("STT: Not available, falling back to keyboard input.")
            try:
                return input("You (type): ").strip()
            except (EOFError, KeyboardInterrupt):
                return ""

        audio = self.record_audio()
        if audio is None or len(audio) < SAMPLERATE * 0.3:
            return ""

        return self.transcribe(audio)


stt_engine = SpeechToText()

__all__ = ["SpeechToText", "stt_engine"]

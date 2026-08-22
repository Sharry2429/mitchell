"""Cross-platform Text-to-Speech engine.

- Windows: pyttsx3 (COM/SAPI)
- macOS: subprocess calling 'say'
- Linux: subprocess calling 'espeak' or 'piper-tts'
- Fallback: print to console
"""

import subprocess
import sys
from typing import Optional

from mitchell.core.logging import logger

# Try pyttsx3 (works on Windows, macOS, Linux with espeak)
try:
    import pyttsx3
    HAS_PYTTSX3 = True
except (ImportError, OSError, Exception):
    HAS_PYTTSX3 = False


class TextToSpeech:
    """Cross-platform text-to-speech engine."""

    def __init__(self) -> None:
        self._engine: Optional[object] = None
        self._backend = "none"
        self._init_engine()

    def _init_engine(self) -> None:
        """Initialize the best available TTS backend for the current platform."""
        if HAS_PYTTSX3:
            try:
                self._engine = pyttsx3.init()
                self._backend = "pyttsx3"
                logger.debug("TTS: Using pyttsx3 backend")
                return
            except Exception as e:
                logger.debug("TTS: pyttsx3 init failed: {}", e)

        if sys.platform == "darwin":
            # macOS 'say' command
            try:
                subprocess.run(["say", "--version"], capture_output=True, check=True)
                self._backend = "macos_say"
                logger.debug("TTS: Using macOS 'say' backend")
                return
            except (FileNotFoundError, subprocess.CalledProcessError):
                pass

        if sys.platform.startswith("linux"):
            # Linux espeak
            try:
                subprocess.run(["espeak", "--version"], capture_output=True, check=True)
                self._backend = "espeak"
                logger.debug("TTS: Using espeak backend")
                return
            except (FileNotFoundError, subprocess.CalledProcessError):
                pass

        self._backend = "console"
        logger.info("TTS: No speech engine found, falling back to console output.")

    def is_available(self) -> bool:
        """Check if a real TTS backend is available."""
        return self._backend != "console" and self._backend != "none"

    def speak(self, text: str) -> None:
        """Speak the given text aloud using the best available backend."""
        if not text.strip():
            return

        logger.debug("TTS [{}]: Speaking '{}'", self._backend, text[:60])

        try:
            if self._backend == "pyttsx3" and self._engine is not None:
                self._engine.say(text)  # type: ignore[union-attr]
                self._engine.runAndWait()  # type: ignore[union-attr]

            elif self._backend == "macos_say":
                subprocess.run(["say", text], check=True, timeout=30)

            elif self._backend == "espeak":
                subprocess.run(["espeak", text], check=True, timeout=30)

            else:
                # Console fallback
                print(f"🔊 Mitchell: {text}")

        except Exception as e:
            logger.error("TTS: Speech error: {}", e)
            print(f"🔊 Mitchell: {text}")


tts_engine = TextToSpeech()

__all__ = ["TextToSpeech", "tts_engine"]

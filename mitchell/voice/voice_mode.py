"""Full voice interaction loop: Listen -> Transcribe -> Query LLM -> Speak Response."""

import time
from typing import List, Optional

from mitchell.core.event_log import event_log
from mitchell.core.logging import logger
from mitchell.voice.stt import stt_engine
from mitchell.voice.tts import tts_engine


WAKE_WORDS: List[str] = ["mitchell", "hey mitchell", "hi mitchell"]


class VoiceMode:
    """Interactive voice conversation loop with wake word detection."""

    def __init__(self) -> None:
        self.stt = stt_engine
        self.tts = tts_engine
        self.is_active = False
        self.awake = False

    def check_wake_word(self, text: str) -> bool:
        """Check if transcribed text contains a wake word."""
        text_lower = text.lower().strip()
        for word in WAKE_WORDS:
            if word in text_lower:
                return True
        return False

    def strip_wake_word(self, text: str) -> str:
        """Remove wake word prefix from transcribed text."""
        text_lower = text.lower().strip()
        for word in sorted(WAKE_WORDS, key=len, reverse=True):
            if text_lower.startswith(word):
                return text[len(word):].strip().lstrip(",").strip()
        return text

    def process_voice_input(self, user_text: str) -> str:
        """Process voice input through the Manager loop and return response text."""
        try:
            from mitchell.manager.loop import manager
            result = manager.run(user_text)
            if isinstance(result, dict):
                return str(result.get("response", result.get("result", str(result))))
            return str(result)
        except Exception as e:
            logger.error("VoiceMode: LLM query error: {}", e)
            return f"Sorry, I encountered an error: {e}"

    def run_loop(self) -> None:
        """Run the continuous voice interaction loop."""
        self.is_active = True
        self.awake = False

        logger.info("VoiceMode: Starting voice interaction loop...")
        self.tts.speak("Mitchell voice mode activated. Say 'hey Mitchell' to wake me up.")

        event_log.log_event(
            "voice_mode_started",
            source="voice_mode",
            data={"wake_words": WAKE_WORDS},
        )

        while self.is_active:
            try:
                text = self.stt.listen()
                if not text:
                    continue

                if not self.awake:
                    if self.check_wake_word(text):
                        self.awake = True
                        command = self.strip_wake_word(text)
                        self.tts.speak("Yes?")

                        if command:
                            logger.info("VoiceMode: Command after wake: '{}'", command)
                            response = self.process_voice_input(command)
                            self.tts.speak(response)
                            self.awake = False
                    continue

                # Already awake — process the command
                if text.lower().strip() in ("stop", "quit", "exit", "go to sleep", "sleep"):
                    self.tts.speak("Going to sleep.")
                    self.awake = False
                    continue

                logger.info("VoiceMode: Processing: '{}'", text)
                response = self.process_voice_input(text)
                self.tts.speak(response)
                self.awake = False

            except KeyboardInterrupt:
                break
            except Exception as e:
                logger.error("VoiceMode loop error: {}", e)
                time.sleep(0.5)

        self.is_active = False
        logger.info("VoiceMode: Stopped.")
        event_log.log_event("voice_mode_stopped", source="voice_mode")

    def stop(self) -> None:
        """Stop the voice loop."""
        self.is_active = False


voice_mode = VoiceMode()

__all__ = ["VoiceMode", "voice_mode"]

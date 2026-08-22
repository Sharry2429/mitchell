"""Voice tools for Mitchell ToolRegistry — cross-platform TTS and STT."""

from mitchell.tools.registry import Tool
from mitchell.voice.tts import tts_engine
from mitchell.voice.stt import stt_engine


def voice_speak(text: str) -> str:
    """Speak text aloud using the best available TTS engine for the current platform."""
    tts_engine.speak(text)
    return f"Spoken: '{text[:80]}'"


def voice_listen() -> str:
    """Listen for speech and transcribe using Groq Whisper API (or keyboard fallback)."""
    text = stt_engine.listen()
    return text if text else "(No speech detected)"


speak_tool = Tool(
    name="voice_speak",
    description="Speak text aloud using platform-native TTS (Windows SAPI / macOS say / Linux espeak).",
    parameters={
        "type": "object",
        "properties": {
            "text": {"type": "string", "description": "Text to speak aloud"}
        },
        "required": ["text"],
    },
    function=voice_speak,
)

listen_tool = Tool(
    name="voice_listen",
    description="Listen for speech via microphone and transcribe using Groq Whisper API.",
    parameters={"type": "object", "properties": {}},
    function=voice_listen,
)

TOOLS = [speak_tool, listen_tool]

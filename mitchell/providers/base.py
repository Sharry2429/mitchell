"""
Base Provider protocol for Mitchell.
"""
from typing import Protocol, Any
from dataclasses import dataclass

@dataclass
class LLMResult:
    content: str
    tool_calls: list[Any] | None = None

class Provider(Protocol):
    name: str

    async def call(
        self,
        messages: list[dict],
        tools: list[dict] | None = None,
        model: str | None = None,
        **kwargs,
    ) -> LLMResult:
        """Execute a call to the LLM provider."""
        ...

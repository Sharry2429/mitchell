"""
Generic OpenAI-compatible provider.
"""
import os
from openai import AsyncOpenAI
from mitchell.providers.base import LLMResult

class OpenAICompatProvider:
    def __init__(self, name: str, base_url: str | None, api_key_env: str, default_model: str):
        self.name = name
        self.base_url = base_url
        self.api_key_env = api_key_env
        self.default_model = default_model
        self._client = None

    @property
    def client(self) -> AsyncOpenAI:
        if self._client is None:
            api_key = os.environ.get(self.api_key_env)
            if not api_key:
                raise ValueError(f"{self.api_key_env} environment variable is not set")
            self._client = AsyncOpenAI(base_url=self.base_url, api_key=api_key)
        return self._client

    async def call(
        self,
        messages: list[dict],
        tools: list[dict] | None = None,
        model: str | None = None,
        **kwargs,
    ) -> LLMResult:
        model_to_use = model or self.default_model
        call_kwargs = {"model": model_to_use, "messages": messages}
        if tools:
            call_kwargs["tools"] = tools
            
        call_kwargs.update(kwargs)

        response = await self.client.chat.completions.create(**call_kwargs)
        message = response.choices[0].message
        
        return LLMResult(
            content=message.content or "",
            tool_calls=message.tool_calls
        )

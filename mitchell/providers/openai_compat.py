import os
from typing import Any, Dict, List, Optional
from openai import OpenAI
from mitchell.providers.base import Provider, LLMResult

class OpenAICompatProvider(Provider):
    def __init__(self, name: str, base_url: str, api_key_env: str, default_model: str):
        self._name = name
        self.base_url = base_url
        self.api_key_env = api_key_env
        self.default_model = default_model
        self._client = None

    @property
    def name(self) -> str:
        return self._name

    def _get_client(self) -> OpenAI:
        if self._client is None:
            api_key = os.environ.get(self.api_key_env)
            if not api_key:
                raise ValueError(f"{self.api_key_env} environment variable is not set")
            self._client = OpenAI(base_url=self.base_url, api_key=api_key)
        return self._client

    def call(self, messages: List[Dict[str, Any]], tools: List[Dict[str, Any]] = None, model: str = None) -> LLMResult:
        client = self._get_client()
        kwargs = {
            "model": model or self.default_model,
            "messages": messages
        }
        if tools:
            kwargs["tools"] = tools
            
        response = client.chat.completions.create(**kwargs)
        message = response.choices[0].message
        
        usage = {
            "prompt_tokens": response.usage.prompt_tokens if response.usage else 0,
            "completion_tokens": response.usage.completion_tokens if response.usage else 0
        }
        
        return LLMResult(
            content=message.content or "",
            tool_calls=[t.model_dump() for t in message.tool_calls] if message.tool_calls else None,
            usage=usage
        )

    def warm_ping(self) -> bool:
        try:
            self.call(messages=[{"role": "user", "content": "ping"}], model=self.default_model)
            return True
        except Exception:
            return False

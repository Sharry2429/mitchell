from typing import Optional
from mitchell.providers.openai_compat import OpenAICompatProvider

class MitchellAPIProvider(OpenAICompatProvider):
    def __init__(self):
        super().__init__(
            name="mitchell_api",
            base_url="http://localhost:7000/v1",
            api_key_env="MITCHELL_API_KEY",
            default_model="gemini-3.7-flash"
        )

    def _get_client(self):
        if self._client is None:
            from openai import OpenAI
            # We use a dummy key because our local mitchell-api router does not require one
            self._client = OpenAI(base_url=self.base_url, api_key="dummy_key")
        return self._client

    def get_model_for_role(self, role: str) -> Optional[str]:
        """Helper to route tasks to specific provider/models via the new router."""
        role = role.lower()
        if role in ("planner", "heavy", "reasoning"):
            return "nvidia/nemotron-3-ultra-550b-a55b"
        elif role in ("stt", "fast", "tool"):
            return "openai/gpt-oss-120b"
        elif role in ("free", "fallback"):
            return "deepseek/deepseek-v4-pro-0813-free:free"
        # Default returns None, which tells mitchell-api to use the standard top-to-bottom cascade
        return None

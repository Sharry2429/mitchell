"""
Groq Provider implementation.
"""
import os
from mitchell.providers.openai_compat import OpenAICompatProvider

class GroqProvider(OpenAICompatProvider):
    def __init__(self):
        super().__init__(
            name="groq",
            base_url=os.environ.get("GROQ_BASE_URL", "https://api.groq.com/openai/v1"),
            api_key_env="GROQ_API_KEY",
            default_model="llama-3.3-70b-versatile"
        )

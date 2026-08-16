"""
AiCredits Provider implementation.
"""
import os
from mitchell.providers.openai_compat import OpenAICompatProvider

class AiCreditsProvider(OpenAICompatProvider):
    def __init__(self):
        super().__init__(
            name="aicredits",
            base_url=os.environ.get("AICREDITS_BASE_URL", "https://api.aicredits.com/v1"),
            api_key_env="AICREDITS_API_KEY",
            default_model="deepseek/deepseek-v4-flash"
        )

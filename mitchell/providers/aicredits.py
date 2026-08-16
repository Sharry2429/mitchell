from mitchell.providers.openai_compat import OpenAICompatProvider

class AiCreditsProvider(OpenAICompatProvider):
    def __init__(self):
        super().__init__(
            name="aicredits",
            base_url="https://api.aicredits.in/v1",
            api_key_env="AICREDITS_API_KEY",
            default_model="deepseek/deepseek-v4-flash"
        )

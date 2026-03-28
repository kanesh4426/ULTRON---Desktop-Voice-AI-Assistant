from ._openai_compatible import OpenAICompatibleProvider


class OpenRouterProvider(OpenAICompatibleProvider):
    base_url = "https://openrouter.ai/api/v1"


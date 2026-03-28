from ._openai_compatible import OpenAICompatibleProvider


class GroqProvider(OpenAICompatibleProvider):
    base_url = "https://api.groq.com/openai/v1"


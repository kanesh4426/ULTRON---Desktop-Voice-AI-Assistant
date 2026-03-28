from abc import ABC, abstractmethod
from typing import AsyncIterator, Dict, List, Optional


class BaseLLMProvider(ABC):
    def __init__(self, api_key: Optional[str], timeout: float = 60.0):
        self.api_key = api_key
        self.timeout = timeout

    @abstractmethod
    def generate(
        self,
        messages: List[Dict[str, str]],
        model: str,
        temperature: float = 0.3,
        max_tokens: int = 1200,
    ) -> str:
        raise NotImplementedError

    async def stream_generate(
        self,
        messages: List[Dict[str, str]],
        model: str,
        temperature: float = 0.3,
        max_tokens: int = 1200,
    ) -> AsyncIterator[str]:
        # Default fallback if provider has no native stream endpoint.
        text = self.generate(messages, model=model, temperature=temperature, max_tokens=max_tokens)
        for token in text.split(" "):
            yield token + " "


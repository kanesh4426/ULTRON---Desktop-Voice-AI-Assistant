from __future__ import annotations

from typing import Dict, Optional, Tuple

from app.llm.providers import BaseLLMProvider


class LLMRouter:
    """
    Simple provider router. Policies can be injected later for cost/latency routing.
    """

    def __init__(self, providers: Dict[str, BaseLLMProvider]) -> None:
        self.providers = providers

    def select(self, name: str, fallback: Optional[str] = None) -> Tuple[str, BaseLLMProvider]:
        if name in self.providers:
            return name, self.providers[name]
        if fallback and fallback in self.providers:
            return fallback, self.providers[fallback]
        raise ValueError(f"Unknown provider: {name}")

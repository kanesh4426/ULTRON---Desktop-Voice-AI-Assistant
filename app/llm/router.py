from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional, Sequence, Tuple

from app.llm.policies import ModelPolicy, SUPPORTED_TASK_TYPES
from app.llm.providers import BaseLLMProvider


CODING_KEYWORDS = (
    "code",
    "bug",
    "debug",
    "fix",
    "traceback",
    "exception",
    "function",
    "class",
    "algorithm",
    "refactor",
    "implement",
    "python",
    "javascript",
    "typescript",
    "sql",
)
SUMMARIZATION_KEYWORDS = (
    "summarize",
    "summary",
    "tldr",
    "tl;dr",
    "recap",
    "briefly",
    "condense",
)
MULTIMODAL_KEYWORDS = (
    "image",
    "photo",
    "screenshot",
    "diagram",
    "chart",
    "vision",
    "ocr",
    "audio",
    "video",
    "pdf",
)
RAG_KEYWORDS = (
    "document",
    "knowledge base",
    "retrieval",
    "file context",
    "company docs",
    "source material",
)


def detect_task(prompt: str, use_rag: bool = False) -> str:
    text = (prompt or "").lower()
    if use_rag:
        return "rag"
    if any(keyword in text for keyword in MULTIMODAL_KEYWORDS):
        return "multimodal"
    if any(keyword in text for keyword in SUMMARIZATION_KEYWORDS):
        return "summarization"
    if any(keyword in text for keyword in CODING_KEYWORDS):
        return "coding"
    if any(keyword in text for keyword in RAG_KEYWORDS):
        return "rag"
    return "general"


@dataclass(frozen=True)
class RoutedProvider:
    name: str
    provider: BaseLLMProvider
    model: str


class LLMRouter:
    """
    Task-aware provider router that can return multiple providers for a single request.
    """

    def __init__(self, providers: Dict[str, BaseLLMProvider], policy: Optional[ModelPolicy] = None) -> None:
        self.providers = providers
        self.policy = policy or ModelPolicy()

    def route(
        self,
        task_type: str,
        preferred: Optional[Sequence[str]] = None,
        model_overrides: Optional[Dict[str, str]] = None,
        default_model_override: Optional[str] = None,
    ) -> List[RoutedProvider]:
        task = task_type if task_type in SUPPORTED_TASK_TYPES else "general"
        names = list(preferred) if preferred else self.policy.providers_for(task)
        return self._resolve_routed_providers(
            names,
            model_overrides=model_overrides,
            default_model_override=default_model_override,
        )

    def fallbacks(
        self,
        task_type: str,
        exclude: Optional[Sequence[str]] = None,
        model_overrides: Optional[Dict[str, str]] = None,
    ) -> List[RoutedProvider]:
        excluded = set(exclude or [])
        names = [name for name in self.policy.fallbacks_for(task_type) if name not in excluded]
        return self._resolve_routed_providers(names, model_overrides=model_overrides)

    def combination_strategy(self, task_type: str, override: Optional[str] = None) -> str:
        return override or self.policy.strategy_for(task_type)

    def run_in_parallel(self, task_type: str, override: Optional[bool] = None) -> bool:
        return self.policy.run_in_parallel_for(task_type) if override is None else override

    def select(self, name: str, fallback: Optional[str] = None) -> Tuple[str, BaseLLMProvider]:
        if name in self.providers:
            return name, self.providers[name]
        if fallback and fallback in self.providers:
            return fallback, self.providers[fallback]
        raise ValueError(f"Unknown provider: {name}")

    def _resolve_routed_providers(
        self,
        names: Sequence[str],
        model_overrides: Optional[Dict[str, str]] = None,
        default_model_override: Optional[str] = None,
    ) -> List[RoutedProvider]:
        requested = self.policy._dedupe(list(names))
        resolved: List[RoutedProvider] = []
        missing: List[str] = []

        for provider_name in requested:
            provider = self.providers.get(provider_name)
            if provider is None:
                missing.append(provider_name)
                continue
            override = (model_overrides or {}).get(provider_name)
            if default_model_override and len(requested) == 1 and not override:
                override = default_model_override
            resolved.append(
                RoutedProvider(
                    name=provider_name,
                    provider=provider,
                    model=self.policy.model_for(provider_name, override=override),
                )
            )

        if resolved:
            return resolved
        if missing:
            raise ValueError("Unknown provider(s): " + ", ".join(missing))

        default_name = self.policy.default_provider
        provider = self.providers.get(default_name)
        if provider is None:
            raise ValueError(f"Unknown provider: {default_name}")
        return [
            RoutedProvider(
                name=default_name,
                provider=provider,
                model=self.policy.model_for(default_name, override=default_model_override),
            )
        ]

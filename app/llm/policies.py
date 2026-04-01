from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set


SUPPORTED_TASK_TYPES = {"coding", "general", "summarization", "multimodal", "rag"}
COMBINATION_STRATEGIES = {"merge", "best", "pipeline"}


@dataclass
class ModelPolicy:
    default_provider: str = "groq"
    default_model: str = "llama-3.3-70b-versatile"
    fallback_provider: Optional[str] = "openrouter"
    provider_models: Dict[str, str] = field(
        default_factory=lambda: {
            "groq": "llama-3.3-70b-versatile",
            "gemini": "gemini-1.5-flash",
            "openrouter": "openai/gpt-4o-mini",
            "huggingface": "mistralai/Mistral-7B-Instruct-v0.2",
        }
    )
    task_routes: Dict[str, List[str]] = field(
        default_factory=lambda: {
            "coding": ["groq"],
            "multimodal": ["gemini"],
            "general": ["groq", "gemini"],
            "summarization": ["groq", "gemini"],
            "rag": ["groq", "gemini"],
        }
    )
    task_fallbacks: Dict[str, List[str]] = field(default_factory=dict)
    task_strategies: Dict[str, str] = field(
        default_factory=lambda: {
            "coding": "best",
            "multimodal": "best",
            "general": "merge",
            "summarization": "best",
            "rag": "pipeline",
        }
    )
    parallel_tasks: Set[str] = field(default_factory=lambda: {"general", "summarization"})
    max_parallel_providers: int = 3

    def __post_init__(self) -> None:
        self.default_provider = self.default_provider or "groq"
        self.default_model = self.default_model or self.provider_models.get(
            self.default_provider,
            "llama-3.3-70b-versatile",
        )
        self.provider_models.setdefault(self.default_provider, self.default_model)
        if not self.task_fallbacks and self.fallback_provider:
            self.task_fallbacks = {task: [self.fallback_provider] for task in self.task_routes}

    def providers_for(self, task_type: str) -> List[str]:
        task = task_type if task_type in SUPPORTED_TASK_TYPES else "general"
        providers = self.task_routes.get(task) or [self.default_provider]
        return self._dedupe(providers)

    def fallbacks_for(self, task_type: str) -> List[str]:
        task = task_type if task_type in SUPPORTED_TASK_TYPES else "general"
        providers = self.task_fallbacks.get(task, [])
        if not providers and self.fallback_provider:
            providers = [self.fallback_provider]
        return [name for name in self._dedupe(providers) if name != self.default_provider]

    def strategy_for(self, task_type: str) -> str:
        task = task_type if task_type in SUPPORTED_TASK_TYPES else "general"
        strategy = self.task_strategies.get(task, "merge")
        return strategy if strategy in COMBINATION_STRATEGIES else "merge"

    def run_in_parallel_for(self, task_type: str) -> bool:
        return task_type in self.parallel_tasks

    def model_for(self, provider_name: str, override: Optional[str] = None) -> str:
        return override or self.provider_models.get(provider_name) or self.default_model

    @staticmethod
    def _dedupe(items: List[str]) -> List[str]:
        seen = set()
        ordered: List[str] = []
        for item in items:
            if not item or item in seen:
                continue
            seen.add(item)
            ordered.append(item)
        return ordered

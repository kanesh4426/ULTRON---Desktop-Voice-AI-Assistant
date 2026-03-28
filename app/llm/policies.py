from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass
class ModelPolicy:
    """
    Placeholder for model selection policies (cost/latency/quality tiers).
    """

    default_provider: str = "groq"
    default_model: str = "llama-3.3-70b-versatile"
    fallback_provider: Optional[str] = None

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class GenerationRequest:
    user_input: str
    provider: Optional[str] = None
    model: Optional[str] = None
    temperature: float = 0.3
    max_tokens: int = 1200
    stream: bool = False
    use_rag: bool = True
    rag_top_k: int = 4
    template_name: Optional[str] = None
    template_vars: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)


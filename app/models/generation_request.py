from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class GenerationRequest:
    user_input: str
    provider: Optional[str] = None
    providers: List[str] = field(default_factory=list)
    model: Optional[str] = None
    provider_models: Dict[str, str] = field(default_factory=dict)
    task_type: Optional[str] = None
    combine_strategy: Optional[str] = None
    parallel: Optional[bool] = None
    enable_multi_llm: bool = True
    temperature: float = 0.3
    max_tokens: int = 1200
    stream: bool = False
    use_rag: bool = True
    rag_top_k: int = 4
    template_name: Optional[str] = None
    template_vars: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)

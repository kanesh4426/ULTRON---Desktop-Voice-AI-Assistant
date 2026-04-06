from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Sequence


def _merge_unique(base: Sequence[str], override: Sequence[str]) -> List[str]:
    ordered: List[str] = []
    seen = set()
    for item in [*base, *override]:
        value = (item or "").strip()
        if not value or value in seen:
            continue
        seen.add(value)
        ordered.append(value)
    return ordered


@dataclass
class StyleDNA:
    persona: str = "Senior editorial strategist"
    brand_voice: str = "Clear, warm, and precise"
    audience: str = "Professional readers"
    tone_anchors: List[str] = field(
        default_factory=lambda: ["confident", "grounded", "helpful"]
    )
    lexical_rules: List[str] = field(default_factory=list)
    banned_phrases: List[str] = field(
        default_factory=lambda: ["as an AI language model"]
    )
    formatting_preferences: List[str] = field(
        default_factory=lambda: [
            "Lead with the answer",
            "Prefer scannable markdown",
            "Use tables when structure improves clarity",
        ]
    )

    def merge(self, override: Optional["StyleDNA"]) -> "StyleDNA":
        if override is None:
            return StyleDNA(
                persona=self.persona,
                brand_voice=self.brand_voice,
                audience=self.audience,
                tone_anchors=list(self.tone_anchors),
                lexical_rules=list(self.lexical_rules),
                banned_phrases=list(self.banned_phrases),
                formatting_preferences=list(self.formatting_preferences),
            )
        return StyleDNA(
            persona=override.persona or self.persona,
            brand_voice=override.brand_voice or self.brand_voice,
            audience=override.audience or self.audience,
            tone_anchors=_merge_unique(self.tone_anchors, override.tone_anchors),
            lexical_rules=_merge_unique(self.lexical_rules, override.lexical_rules),
            banned_phrases=_merge_unique(self.banned_phrases, override.banned_phrases),
            formatting_preferences=_merge_unique(
                self.formatting_preferences,
                override.formatting_preferences,
            ),
        )


@dataclass
class GroundingHit:
    path: str
    excerpt: str
    score: Optional[float] = None

    @classmethod
    def from_mapping(cls, payload: Dict[str, Any]) -> "GroundingHit":
        return cls(
            path=str(payload.get("path", "")),
            excerpt=str(
                payload.get("excerpt")
                or payload.get("chunk")
                or payload.get("content")
                or ""
            ),
            score=payload.get("score"),
        )


@dataclass
class DeltaUpdate:
    operation: str
    target: str = ""
    content: str = ""
    occurrence: int = 1


@dataclass
class ContentGenerationRequest:
    user_input: str
    session_id: str = "default"
    content_type: str = "article"
    title: Optional[str] = None
    provider: Optional[str] = None
    model: Optional[str] = None
    temperature: float = 0.4
    max_tokens: int = 1800
    use_rag: bool = False
    rag_top_k: int = 4
    document_query: Optional[str] = None
    document_hits: List[GroundingHit | Dict[str, Any]] = field(default_factory=list)
    style_dna: Optional[StyleDNA] = None
    target_sections: List[str] = field(default_factory=list)
    persist_output: bool = False
    output_dir: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ContentGenerationResult:
    success: bool
    content: str = ""
    raw_content: str = ""
    provider: Optional[str] = None
    model: Optional[str] = None
    session_id: str = "default"
    content_type: str = "article"
    style_dna: StyleDNA = field(default_factory=StyleDNA)
    grounding_hits: List[GroundingHit] = field(default_factory=list)
    quality_issues: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    filepath: Optional[str] = None
    attempts: int = 0
    error: Optional[str] = None
    updated_from_delta: bool = False

    def to_legacy_dict(self) -> Dict[str, Any]:
        payload = {
            "success": self.success,
            "content": self.content,
            "filepath": self.filepath,
            "content_type": self.content_type,
            "quality_issues": list(self.quality_issues),
            "attempts": self.attempts,
            "provider": self.provider,
            "model": self.model,
            "metadata": dict(self.metadata),
        }
        if self.error:
            payload["error"] = self.error
        return payload

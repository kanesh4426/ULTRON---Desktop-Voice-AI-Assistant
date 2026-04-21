from __future__ import annotations

import os
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from app.utils.config import AssistantConfig
from app.orchestration.workflow_runner import AssistantEngine
from app.models.generation_request import GenerationRequest

from .engine import ContentGenerationEngine
from .models import ContentGenerationRequest
from .style_dna import StyleDNA


CONTENT_TYPE_STYLES = {
    "blog": StyleDNA(
        persona="Editorial storyteller",
        brand_voice="Warm, sharp, and approachable",
        audience="Curious readers",
        tone_anchors=["conversational", "insightful", "confident"],
    ),
    "article": StyleDNA(
        persona="Research-backed writer",
        brand_voice="Clear, calm, and well-supported",
        audience="Professional readers",
        tone_anchors=["structured", "credible", "helpful"],
    ),
    "technical": StyleDNA(
        persona="Technical documentation lead",
        brand_voice="Precise, grounded, and direct",
        audience="Technical teams",
        tone_anchors=["accurate", "succinct", "systematic"],
    ),
    "creative": StyleDNA(
        persona="Brand narrative director",
        brand_voice="Vivid, human, and polished",
        audience="Audience-facing readers",
        tone_anchors=["evocative", "memorable", "energetic"],
    ),
}


class ContentGenerator(ContentGenerationEngine):
    """
    Dedicated high-fidelity content generation role.
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        *,
        config: Optional[AssistantConfig] = None,
        **engine_kwargs: Any,
    ) -> None:
        resolved_config = config or AssistantConfig.from_env()
        if api_key:
            resolved_config.provider = "gemini"
            resolved_config.model = "gemini-1.5-flash"
            resolved_config.gemini_api_key = api_key
        super().__init__(config=resolved_config, **engine_kwargs)
        self.session_id = f"content-role-{id(self)}"

    def generate_content(
        self,
        prompt: str,
        content_type: str = "article",
        custom_config: Optional[Dict[str, Any]] = None,
        min_quality_standard: bool = True,
        retry_count: int = 2,
    ) -> Dict[str, Any]:
        options = custom_config or {}
        req = ContentGenerationRequest(
            user_input=prompt,
            content_type=content_type,
            session_id=self.session_id,
            style_dna=options.get("style_dna"),
            use_rag=bool(options.get("use_rag", False)),
            rag_top_k=int(options.get("rag_top_k", self.config.rag_top_k)),
            temperature=float(options.get("temperature", 0.4)),
            max_tokens=int(options.get("max_output_tokens", 1800)),
            provider=options.get("provider"),
            model=options.get("model"),
            persist_output=options.get("persist_output", True),
            output_dir=options.get("output_dir"),
            metadata={"additional_instructions": options.get("additional_instructions", "")},
        )
        
        attempts = max(retry_count + 1, 1)
        last_result = None
        for _ in range(attempts):
            result = self.generate(req)
            last_result = result
            if not min_quality_standard or not result.quality_issues:
                break

        return {
            "success": last_result.success,
            "content": last_result.content,
            "error": last_result.error,
            "provider_used": last_result.provider,
            "quality_issues": last_result.quality_issues,
            "attempts": last_result.attempts,
            "filepath": last_result.filepath,
            "metadata": last_result.metadata,
            "content_type": last_result.content_type,
        }

    def batch_generate(self, prompts: List[str], content_type: str = "article", **kwargs: Any) -> List[Dict[str, Any]]:
        return [
            self.generate_content(prompt, content_type=content_type, custom_config=kwargs)
            for prompt in prompts
        ]

    def apply_delta_update(
        self,
        *,
        delta,
        original_content: Optional[str] = None,
        session_id: Optional[str] = None,
        content_type: str = "article",
        persist_output: bool = False,
        output_dir: Optional[str] = None,
        metadata: Optional[Dict[str, str]] = None,
    ) -> Dict[str, Any]:
        result = self.apply_delta(
            session_id=session_id or self.session_id,
            delta=delta,
            original_content=original_content,
            content_type=content_type,
            persist_output=persist_output,
            output_dir=output_dir,
            metadata=metadata,
        )
        return result.to_legacy_dict()


def generate_content(
    topic: str,
    content_type: str = "article",
    **kwargs: Any,
) -> Dict[str, Any]:
    generator = ContentGenerator()
    return generator.generate_content(topic, content_type=content_type, custom_config=kwargs or None)

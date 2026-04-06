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

    def _validate_content_quality(self, content: str, min_length: int = 200) -> Tuple[bool, List[str]]:
        issues = self.validate_output(content)
        if len((content or "").strip()) < min_length:
            issues.append(f"Content too short ({len(content or '')} characters)")
        return len(issues) == 0, issues

    def _resolve_style(self, content_type: str, custom_config: Optional[Dict[str, Any]]) -> StyleDNA:
        base = CONTENT_TYPE_STYLES.get(content_type, CONTENT_TYPE_STYLES["article"])
        style_override = (custom_config or {}).get("style_dna")
        if isinstance(style_override, dict):
            style_override = StyleDNA(**style_override)
        if isinstance(style_override, StyleDNA):
            return base.merge(style_override)
        return base

    def generate_content(
        self,
        prompt: str,
        content_type: str = "article",
        custom_config: Optional[Dict[str, Any]] = None,
        min_quality_standard: bool = True,
        retry_count: int = 2,
    ) -> Dict[str, Any]:
        content_type = content_type if content_type in CONTENT_TYPE_STYLES else "article"
        options = custom_config or {}
        style_dna = self._resolve_style(content_type, options)

        full_prompt = (
            f"You are a professional content creator.\n"
            f"Task: Write a {content_type} based on the following topic:\n{prompt}\n\n"
            f"Style Guidelines:\n"
            f"- Persona: {style_dna.persona}\n"
            f"- Voice: {style_dna.brand_voice}\n"
            f"- Audience: {style_dna.audience}\n"
            f"- Tone: {', '.join(style_dna.tone_anchors)}\n"
        )
        if options.get("additional_instructions"):
            full_prompt += f"\nAdditional Instructions: {options['additional_instructions']}\n"

        providers_list = ["groq", "gemini", "openrouter"]
        if options.get("provider") and options.get("provider") not in providers_list:
            providers_list.insert(0, options.get("provider"))

        request = GenerationRequest(
            user_input=full_prompt,
            task_type="general",
            enable_multi_llm=True,
            providers=providers_list,
            combine_strategy="best",
            temperature=float(options.get("temperature", 0.4)),
            max_tokens=int(options.get("max_output_tokens", 1800)),
            use_rag=bool(options.get("use_rag", False)),
            rag_top_k=int(options.get("rag_top_k", self.config.rag_top_k)),
        )

        engine = AssistantEngine(self.config)
        last_result_dict = None
        attempts = max(retry_count + 1, 1)
        
        for attempt in range(1, attempts + 1):
            result = engine.generate(request)
            if not result.get("success"):
                last_result_dict = {
                    "success": False,
                    "error": result.get("response", "Generation failed"),
                    "attempts": attempt
                }
                continue
            
            content = result.get("response", "")
            is_valid, issues = self._validate_content_quality(content)
            
            last_result_dict = {
                "success": True,
                "content": content,
                "provider_used": result.get("provider"),
                "quality_issues": issues,
                "attempts": attempt,
                "metadata": {"generated_at": datetime.now().isoformat()}
            }

            if options.get("persist_output", True):
                output_dir = options.get("output_dir") or os.path.join(os.getcwd(), "Database", "other")
                os.makedirs(output_dir, exist_ok=True)
                filename = f"generated_{content_type}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
                filepath = os.path.join(output_dir, filename)
                with open(filepath, "w", encoding="utf-8") as f:
                    f.write(content)
                last_result_dict["filepath"] = filepath

            if not min_quality_standard or is_valid:
                break

        if last_result_dict is None:
            return {
                "success": False,
                "error": "Content generation did not produce a result.",
                "attempts": attempts,
            }
        return last_result_dict

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

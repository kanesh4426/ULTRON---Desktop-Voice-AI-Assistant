from __future__ import annotations

from typing import Dict, Optional

from .models import StyleDNA


DEFAULT_STYLE_DNA = StyleDNA()


class SessionStyleRegistry:
    def __init__(self, default_style: Optional[StyleDNA] = None) -> None:
        self.default_style = default_style or DEFAULT_STYLE_DNA
        self._styles: Dict[str, StyleDNA] = {}

    def resolve(self, session_id: str, override: Optional[StyleDNA] = None) -> StyleDNA:
        base = self._styles.get(session_id, self.default_style)
        resolved = base.merge(override)
        self._styles[session_id] = resolved
        return resolved

    def get(self, session_id: str) -> StyleDNA:
        return self._styles.get(session_id, self.default_style)


def build_style_instruction(style_dna: StyleDNA) -> str:
    lines = [
        "Style DNA:",
        f"- Persona: {style_dna.persona}",
        f"- Brand voice: {style_dna.brand_voice}",
        f"- Audience: {style_dna.audience}",
        f"- Tone anchors: {', '.join(style_dna.tone_anchors)}",
        f"- Formatting preferences: {', '.join(style_dna.formatting_preferences)}",
    ]
    if style_dna.lexical_rules:
        lines.append(f"- Lexical rules: {', '.join(style_dna.lexical_rules)}")
    if style_dna.banned_phrases:
        lines.append(f"- Avoid phrases: {', '.join(style_dna.banned_phrases)}")
    return "\n".join(lines)

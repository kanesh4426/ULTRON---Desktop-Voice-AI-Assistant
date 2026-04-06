from __future__ import annotations

import re
from typing import List, Sequence

from .models import GroundingHit, StyleDNA


class StructuredMarkdownFormatter:
    def format(
        self,
        *,
        prompt: str,
        raw_content: str,
        title: str | None,
        content_type: str,
        style_dna: StyleDNA,
        grounding_hits: Sequence[GroundingHit],
        session_id: str,
        provider: str | None,
        model: str | None,
    ) -> str:
        body = self._normalize_body(raw_content)
        resolved_title = self._derive_title(title, prompt, raw_content)
        overview = self._derive_overview(body, prompt)

        blocks = [
            f"# {resolved_title}",
            "",
            "> [!NOTE]",
            f"> Persona: {style_dna.persona}",
            f"> Voice: {style_dna.brand_voice}",
            f"> Tone anchors: {', '.join(style_dna.tone_anchors)}",
            "",
            "## Overview",
            overview,
            "",
            "## Response",
            body,
            "",
            "## Metadata",
            "| Field | Value |",
            "| --- | --- |",
            f"| Content Type | {self._table_escape(content_type)} |",
            f"| Audience | {self._table_escape(style_dna.audience)} |",
            f"| Session | {self._table_escape(session_id)} |",
            f"| Provider | {self._table_escape(provider or 'unknown')} |",
            f"| Model | {self._table_escape(model or 'unknown')} |",
            "",
            "## Grounding",
            "| Source | Evidence |",
            "| --- | --- |",
        ]

        if grounding_hits:
            for hit in grounding_hits:
                blocks.append(
                    f"| {self._table_escape(hit.path)} | {self._table_escape(self._trim(hit.excerpt, 180))} |"
                )
        else:
            blocks.append("| None supplied | No document grounding requested for this turn. |")

        return "\n".join(blocks).strip() + "\n"

    def validate(self, content: str) -> List[str]:
        issues: List[str] = []
        stripped = (content or "").lstrip()
        if not stripped.startswith("# "):
            issues.append("Missing top-level markdown heading")
        if "> [!" not in content:
            issues.append("Missing markdown callout")
        if "## Overview" not in content or "## Response" not in content:
            issues.append("Missing required markdown hierarchy")
        if "| Field | Value |" not in content:
            issues.append("Missing metadata table")
        if "| Source | Evidence |" not in content:
            issues.append("Missing grounding table")
        return issues

    def _normalize_body(self, raw_content: str) -> str:
        cleaned = (raw_content or "").strip()
        if not cleaned:
            return "No body content was generated."
        lines = cleaned.splitlines()
        if lines and lines[0].lstrip().startswith("#"):
            cleaned = "\n".join(lines[1:]).strip() or cleaned
        return cleaned

    def _derive_title(self, title: str | None, prompt: str, raw_content: str) -> str:
        if title and title.strip():
            return title.strip()
        for line in (raw_content or "").splitlines():
            stripped = line.strip()
            if stripped.startswith("#"):
                return stripped.lstrip("#").strip()
        words = re.findall(r"[A-Za-z0-9']+", prompt or "")
        if not words:
            return "Generated Content"
        return " ".join(
            word if word.isupper() else word.capitalize()
            for word in words[:8]
        )

    def _derive_overview(self, body: str, prompt: str) -> str:
        for paragraph in [part.strip() for part in body.split("\n\n") if part.strip()]:
            if paragraph.startswith("#"):
                continue
            return self._trim(paragraph, 280)
        return self._trim(prompt or "Structured response generated.", 280)

    @staticmethod
    def _trim(value: str, limit: int) -> str:
        text = " ".join((value or "").split())
        if len(text) <= limit:
            return text
        return text[: limit - 3].rstrip() + "..."

    @staticmethod
    def _table_escape(value: str) -> str:
        return (value or "").replace("|", "\\|").replace("\n", "<br>")

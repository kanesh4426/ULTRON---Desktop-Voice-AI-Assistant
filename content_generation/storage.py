from __future__ import annotations

import re
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional


class ContentArtifactStore:
    FOLDER_MAP = {
        "blog": "blogs",
        "article": "articles",
        "technical": "technical",
        "creative": "creative",
    }

    def __init__(self, base_dir: str = "data/content") -> None:
        self.base_dir = Path(base_dir)

    def save(
        self,
        *,
        content: str,
        prompt: str,
        content_type: str,
        metadata: Optional[Dict[str, str]] = None,
        output_dir: Optional[str] = None,
    ) -> str:
        root = Path(output_dir) if output_dir else self.base_dir
        folder = root / self.FOLDER_MAP.get(content_type, "other")
        folder.mkdir(parents=True, exist_ok=True)

        filename = self._build_filename(prompt=prompt, content_type=content_type)
        target = folder / filename
        payload = self._with_metadata_comment(content, metadata or {})
        target.write_text(payload, encoding="utf-8")
        return str(target)

    @staticmethod
    def _build_filename(prompt: str, content_type: str) -> str:
        slug = re.sub(r"[^a-z0-9]+", "-", (prompt or "content").lower()).strip("-")
        slug = slug[:60] or "content"
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        return f"{content_type}_{slug}_{stamp}.md"

    @staticmethod
    def _with_metadata_comment(content: str, metadata: Dict[str, str]) -> str:
        if not metadata:
            return content
        lines = ["<!--"]
        for key, value in metadata.items():
            lines.append(f"{key}: {value}")
        lines.append("-->")
        lines.append("")
        lines.append(content)
        return "\n".join(lines)

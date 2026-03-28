from pathlib import Path
from typing import Any, Dict


class PromptTemplateEngine:
    def __init__(self, template_dir: str):
        self.template_dir = Path(template_dir)

    def render(self, template_name: str, variables: Dict[str, Any]) -> str:
        path = self.template_dir / template_name
        if not path.exists():
            raise FileNotFoundError(f"Template not found: {path}")
        raw = path.read_text(encoding="utf-8")
        return raw.format(**variables)


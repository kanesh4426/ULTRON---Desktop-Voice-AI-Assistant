from __future__ import annotations

from typing import Dict

from app.prompts.template_engine import PromptTemplateEngine


class PromptRegistry:
    """
    Simple prompt registry facade over PromptTemplateEngine.
    """

    def __init__(self, template_dir: str) -> None:
        self.engine = PromptTemplateEngine(template_dir)

    def render(self, name: str, variables: Dict[str, str]) -> str:
        return self.engine.render(name, variables)

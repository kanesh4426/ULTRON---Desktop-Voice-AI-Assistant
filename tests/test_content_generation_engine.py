import tempfile
import unittest
from pathlib import Path
from typing import Optional

from content_generation import (
    ContentGenerationEngine,
    ContentGenerationRequest,
    DeltaUpdate,
    StaticGrounder,
    StyleDNA,
)
from app.llm.providers.base_provider import BaseLLMProvider
from app.utils.config import AssistantConfig


class FakeProvider(BaseLLMProvider):
    def __init__(self, response: str):
        super().__init__(api_key="test-key", timeout=1.0)
        self.response = response
        self.calls = []

    def generate(
        self,
        messages,
        model: str,
        temperature: float = 0.3,
        max_tokens: int = 1200,
    ) -> str:
        self.calls.append(
            {
                "messages": messages,
                "model": model,
                "temperature": temperature,
                "max_tokens": max_tokens,
            }
        )
        return self.response


class TestContentGenerationEngine(unittest.TestCase):
    def _build_engine(
        self,
        provider: Optional[FakeProvider] = None,
        grounder: Optional[StaticGrounder] = None,
    ) -> tuple[ContentGenerationEngine, FakeProvider]:
        tempdir = tempfile.TemporaryDirectory(dir=str(Path.cwd()))
        self.addCleanup(tempdir.cleanup)
        config = AssistantConfig(
            provider="groq",
            model="llama-3.3-70b-versatile",
            workspace_root=tempdir.name,
            rag_store_path=str(Path(tempdir.name) / "rag"),
            rag_top_k=2,
            request_timeout=1.0,
            groq_api_key="test",
            gemini_api_key="test",
            huggingface_api_key="test",
            openrouter_api_key="test",
        )
        fake_provider = provider or FakeProvider(
            "Ship the launch summary with crisp milestones and clear next steps."
        )
        engine = ContentGenerationEngine(
            config=config,
            providers={
                "groq": fake_provider,
                "gemini": fake_provider,
                "huggingface": fake_provider,
                "openrouter": fake_provider,
            },
            grounder=grounder or StaticGrounder([]),
        )
        return engine, fake_provider

    def test_style_dna_persists_across_multiple_turns(self) -> None:
        engine, _ = self._build_engine(FakeProvider("Keep the release narrative calm and evidence-based."))
        style = StyleDNA(
            persona="Boardroom analyst",
            brand_voice="Measured and exact",
            audience="Executives",
            tone_anchors=["measured", "decisive"],
        )

        first = engine.generate(
            ContentGenerationRequest(
                user_input="Write a release note summary.",
                session_id="tone-session",
                style_dna=style,
            )
        )
        second = engine.generate(
            ContentGenerationRequest(
                user_input="Now write a follow-up update for the same audience.",
                session_id="tone-session",
            )
        )

        self.assertTrue(first.success)
        self.assertTrue(second.success)
        self.assertIn("Voice: Measured and exact", first.content)
        self.assertIn("Voice: Measured and exact", second.content)
        self.assertIn("measured", second.content)
        self.assertIn("decisive", second.content)

    def test_grounding_hits_are_injected_and_rendered(self) -> None:
        grounder = StaticGrounder(
            [
                {
                    "path": "docs/product.md",
                    "chunk": "Retention improved by 18% after the onboarding changes.",
                }
            ]
        )
        provider = FakeProvider("Use the onboarding result to support the recommendation.")
        engine, fake_provider = self._build_engine(provider=provider, grounder=grounder)

        result = engine.generate(
            ContentGenerationRequest(
                user_input="Summarize the product impact.",
                session_id="grounded-session",
                use_rag=True,
            )
        )

        self.assertTrue(result.success)
        self.assertIn("docs/product.md", result.content)
        self.assertIn("Retention improved by 18%", result.content)
        system_message = fake_provider.calls[0]["messages"][0]["content"]
        self.assertIn("Retention improved by 18%", system_message)

    def test_structured_markdown_contains_hierarchy_callout_and_tables(self) -> None:
        engine, _ = self._build_engine(
            FakeProvider("Launch highlights include faster setup and lower friction for onboarding.")
        )

        result = engine.generate(
            ContentGenerationRequest(
                user_input="Draft launch highlights for customers.",
                session_id="markdown-session",
            )
        )

        self.assertTrue(result.success)
        self.assertTrue(result.content.startswith("# "))
        self.assertIn("> [!NOTE]", result.content)
        self.assertIn("## Overview", result.content)
        self.assertIn("## Response", result.content)
        self.assertIn("| Field | Value |", result.content)
        self.assertIn("| Source | Evidence |", result.content)

    def test_delta_updates_replace_inline_content_without_full_regeneration(self) -> None:
        engine, _ = self._build_engine()
        original = (
            "# Weekly Update\n\n"
            "## Response\n"
            "The retention lift reached 18% after the experiment.\n\n"
            "## Metadata\n"
            "| Field | Value |\n"
            "| --- | --- |\n"
            "| Session | delta-session |\n\n"
            "## Grounding\n"
            "| Source | Evidence |\n"
            "| --- | --- |\n"
            "| docs/product.md | Retention improved by 18%. |\n"
        )

        result = engine.apply_delta(
            session_id="delta-session",
            original_content=original,
            delta=DeltaUpdate(operation="replace", target="18%", content="24%"),
        )

        self.assertTrue(result.success)
        self.assertIn("24%", result.content)
        self.assertNotIn("18% after the experiment", result.content)


if __name__ == "__main__":
    unittest.main()



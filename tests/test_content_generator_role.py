import tempfile
import unittest
from pathlib import Path

from content_generation import ContentGenerator, StaticGrounder
from app.llm.providers.base_provider import BaseLLMProvider
from app.utils.config import AssistantConfig


class FakeProvider(BaseLLMProvider):
    def __init__(self, response: str):
        super().__init__(api_key="test-key", timeout=1.0)
        self.response = response

    def generate(
        self,
        messages,
        model: str,
        temperature: float = 0.3,
        max_tokens: int = 1200,
    ) -> str:
        return self.response


class TestContentGeneratorRole(unittest.TestCase):
    def test_role_surface_returns_structured_result_and_persists_markdown(self) -> None:
        tempdir = tempfile.TemporaryDirectory(dir=str(Path.cwd()))
        self.addCleanup(tempdir.cleanup)
        config = AssistantConfig(
            provider="groq",
            model="llama-3.3-70b-versatile",
            workspace_root=tempdir.name,
            rag_store_path=str(Path(tempdir.name) / "rag"),
            request_timeout=1.0,
            groq_api_key="test",
            gemini_api_key="test",
            huggingface_api_key="test",
            openrouter_api_key="test",
        )
        generator = ContentGenerator(
            config=config,
            providers={
                "groq": FakeProvider("Deliver a structured technical brief with a clear recommendation."),
                "gemini": FakeProvider("unused"),
                "huggingface": FakeProvider("unused"),
                "openrouter": FakeProvider("unused"),
            },
            grounder=StaticGrounder([]),
        )

        result = generator.generate_content(
            "Create a technical update for the onboarding team.",
            content_type="technical",
            custom_config={"output_dir": tempdir.name},
        )

        self.assertTrue(result["success"])
        self.assertEqual("technical", result["content_type"])
        self.assertTrue(result["filepath"].endswith(".md"))
        self.assertTrue(Path(result["filepath"]).exists())
        self.assertIn("## Metadata", result["content"])
        self.assertIn("Voice: Precise, grounded, and direct", result["content"])

    def test_role_surface_supports_non_persistent_runs(self) -> None:
        tempdir = tempfile.TemporaryDirectory(dir=str(Path.cwd()))
        self.addCleanup(tempdir.cleanup)
        config = AssistantConfig(
            provider="groq",
            model="llama-3.3-70b-versatile",
            workspace_root=tempdir.name,
            rag_store_path=str(Path(tempdir.name) / "rag"),
            request_timeout=1.0,
            groq_api_key="test",
            gemini_api_key="test",
            huggingface_api_key="test",
            openrouter_api_key="test",
        )
        generator = ContentGenerator(
            config=config,
            providers={
                "groq": FakeProvider("Write a concise customer-facing launch update."),
                "gemini": FakeProvider("unused"),
                "huggingface": FakeProvider("unused"),
                "openrouter": FakeProvider("unused"),
            },
            grounder=StaticGrounder([]),
        )

        result = generator.generate_content(
            "Draft a short launch note.",
            custom_config={"persist_output": False},
        )

        self.assertTrue(result["success"])
        self.assertIsNone(result["filepath"])
        self.assertIn("## Response", result["content"])
        self.assertIn("| Field | Value |", result["content"])


if __name__ == "__main__":
    unittest.main()



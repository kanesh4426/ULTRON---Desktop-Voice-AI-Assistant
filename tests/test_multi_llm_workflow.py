import tempfile
import unittest
from pathlib import Path
from typing import Dict, Optional

from app.llm.policies import ModelPolicy
from app.llm.providers.base_provider import BaseLLMProvider
from app.llm.router import LLMRouter, detect_task
from app.models.generation_request import GenerationRequest
from app.orchestration.workflow_runner import AssistantEngine
from app.utils.config import AssistantConfig


class FakeProvider(BaseLLMProvider):
    def __init__(self, response: str = "", error: Optional[str] = None):
        super().__init__(api_key="test-key", timeout=1.0)
        self.response = response
        self.error = error
        self.calls = []

    def generate(
        self,
        messages,
        model: str,
        temperature: float = 0.3,
        max_tokens: int = 1200,
    ) -> str:
        self.calls.append({
            "messages": messages,
            "model": model,
            "temperature": temperature,
            "max_tokens": max_tokens,
        })
        if self.error:
            raise RuntimeError(self.error)
        return self.response


class TestMultiLLMWorkflow(unittest.TestCase):
    def _build_engine(self, providers: Dict[str, FakeProvider]) -> AssistantEngine:
        tempdir = tempfile.TemporaryDirectory()
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
        engine = AssistantEngine(config)
        engine.providers = providers
        engine.router.providers = providers
        return engine

    def test_detect_task_classifies_supported_queries(self) -> None:
        self.assertEqual(detect_task("Summarize this article"), "summarization")
        self.assertEqual(detect_task("Fix this Python bug"), "coding")
        self.assertEqual(detect_task("Analyze this image"), "multimodal")
        self.assertEqual(detect_task("Use company docs"), "rag")
        self.assertEqual(detect_task("Tell me a joke"), "general")

    def test_router_returns_multiple_providers_for_general_tasks(self) -> None:
        router = LLMRouter(
            {
                "groq": FakeProvider(),
                "gemini": FakeProvider(),
                "openrouter": FakeProvider(),
            },
            policy=ModelPolicy(),
        )
        routed = router.route("general")
        self.assertEqual(["groq", "gemini"], [item.name for item in routed])

    def test_general_requests_merge_parallel_responses(self) -> None:
        engine = self._build_engine(
            {
                "groq": FakeProvider(response="Groq answer"),
                "gemini": FakeProvider(response="Gemini answer"),
                "huggingface": FakeProvider(response="HF answer"),
                "openrouter": FakeProvider(response="OpenRouter answer"),
            }
        )
        result = engine.generate(GenerationRequest(user_input="Explain batteries simply", use_rag=False))

        self.assertTrue(result["success"])
        self.assertEqual("general", result["task_type"])
        self.assertEqual(["groq", "gemini"], result["providers"])
        self.assertIn("Groq answer", result["response"])
        self.assertIn("Gemini answer", result["response"])

    def test_rag_requests_use_pipeline_strategy(self) -> None:
        providers = {
            "groq": FakeProvider(response="Draft answer"),
            "gemini": FakeProvider(response="Refined answer"),
            "huggingface": FakeProvider(response="HF answer"),
            "openrouter": FakeProvider(response="Fallback answer"),
        }
        engine = self._build_engine(providers)
        result = engine.generate(GenerationRequest(user_input="Use the docs to answer this", use_rag=True))

        self.assertTrue(result["success"])
        self.assertEqual("pipeline", result["combine_strategy"])
        self.assertEqual("Refined answer", result["response"])
        gemini_messages = providers["gemini"].calls[0]["messages"]
        self.assertTrue(any(message.get("content") == "Draft answer" for message in gemini_messages))

    def test_fallback_provider_is_used_when_primary_route_fails(self) -> None:
        engine = self._build_engine(
            {
                "groq": FakeProvider(error="groq failure"),
                "gemini": FakeProvider(error="gemini failure"),
                "huggingface": FakeProvider(response="HF answer"),
                "openrouter": FakeProvider(response="Fallback answer"),
            }
        )
        result = engine.generate(GenerationRequest(user_input="Tell me something useful", use_rag=False))

        self.assertTrue(result["success"])
        self.assertEqual(["openrouter"], result["providers"])
        self.assertEqual(2, len(result["failures"]))
        self.assertEqual("Fallback answer", result["response"])


if __name__ == "__main__":
    unittest.main()

import asyncio
import json
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import asdict, dataclass
from pathlib import Path
from time import perf_counter
from typing import Any, Callable, Dict, List, Optional, Sequence, Tuple

from app.agents.planner import AgentPlanner
from app.llm import LLMRouter, ModelPolicy, detect_task
from app.llm.providers import GeminiProvider, GroqProvider, HuggingFaceProvider, OpenRouterProvider
from app.llm.router import RoutedProvider
from app.llm.streaming.response_streamer import ResponseStreamer
from app.models.generation_request import GenerationRequest
from app.prompts.template_engine import PromptTemplateEngine
from app.rag import DocumentLoader, EmbeddingModel, Retriever, TextChunker, VectorStore
from app.tools.executor import ToolExecutor
from app.tools.registry import SystemToolRegistry
from app.utils.config import AssistantConfig
from app.utils.logger import get_logger


@dataclass
class ProviderExecutionResult:
    provider_name: str
    model: str
    response: str = ""
    error: Optional[str] = None
    latency_ms: float = 0.0


class AssistantEngine:
    def __init__(self, config: AssistantConfig):
        self.config = config
        self.logger = get_logger("assistant.engine")

        self.providers = {
            "groq": GroqProvider(config.groq_api_key, timeout=config.request_timeout),
            "gemini": GeminiProvider(config.gemini_api_key, timeout=config.request_timeout),
            "huggingface": HuggingFaceProvider(config.huggingface_api_key, timeout=config.request_timeout),
            "openrouter": OpenRouterProvider(config.openrouter_api_key, timeout=config.request_timeout),
        }
        self.policy = ModelPolicy(default_provider=config.provider, default_model=config.model)
        self.router = LLMRouter(self.providers, policy=self.policy)

        self.registry = SystemToolRegistry(workspace_root=config.workspace_root)
        self.planner = AgentPlanner()
        self.tool_executor = ToolExecutor(self.registry)
        self.streamer = ResponseStreamer()

        self.template_engine = PromptTemplateEngine(
            template_dir=str(Path(__file__).resolve().parents[1] / "prompts" / "templates")
        )

        self.doc_loader = DocumentLoader()
        self.chunker = TextChunker()
        self.embedding_model = EmbeddingModel()
        self.vector_store = VectorStore(config.rag_store_path)
        self.retriever = Retriever(self.embedding_model, self.vector_store)

    def switch_provider(self, provider_name: str, model: Optional[str] = None) -> None:
        if provider_name not in self.providers:
            raise ValueError(f"Unknown provider: {provider_name}")
        self.config.provider = provider_name
        self.policy.default_provider = provider_name
        if model:
            self.config.model = model
            self.policy.default_model = model
            self.policy.provider_models[provider_name] = model

    def ingest_documents(self, directory_path: str) -> Dict[str, Any]:
        docs = self.doc_loader.load_from_directory(directory_path, recursive=True)
        chunks = self.chunker.chunk_documents(docs)
        embeddings = self.embedding_model.embed([c["chunk"] for c in chunks])
        metadata = [{"path": c["path"], "chunk": c["chunk"]} for c in chunks]
        self.vector_store.add(embeddings, metadata)
        return {"success": True, "documents": len(docs), "chunks": len(chunks)}

    def _build_messages(self, req: GenerationRequest) -> List[Dict[str, str]]:
        query = req.user_input
        context_blocks: List[str] = []
        if req.use_rag:
            hits = self.retriever.retrieve(query, top_k=req.rag_top_k or self.config.rag_top_k)
            for hit in hits:
                context_blocks.append("Source: {}\n{}".format(hit.get("path"), hit.get("chunk")))

        tool_call = self.planner.plan(query)
        tool_result = None
        if tool_call:
            tool_result = self.tool_executor.execute(tool_call)

        if req.template_name:
            prompt = self.template_engine.render(req.template_name, req.template_vars)
            query = f"{prompt}\n\nUser request: {query}"

        system_parts = [
            "You are a programmable AI assistant.",
            "If context is provided, use it accurately.",
            "If tool output is provided, treat it as trusted execution result.",
        ]
        if context_blocks:
            system_parts.append("Retrieved context:\n" + "\n\n".join(context_blocks))
        if tool_result is not None:
            system_parts.append("Tool output:\n" + json.dumps(tool_result, ensure_ascii=False))

        return [
            {"role": "system", "content": "\n\n".join(system_parts)},
            {"role": "user", "content": query},
        ]

    def _detect_task(self, req: GenerationRequest) -> str:
        if req.task_type:
            return req.task_type
        return detect_task(req.user_input, use_rag=req.use_rag)

    def _model_overrides(self, req: GenerationRequest) -> Dict[str, str]:
        overrides = dict(req.provider_models)
        if req.provider and req.model:
            overrides.setdefault(req.provider, req.model)
        elif len(req.providers) == 1 and req.model:
            overrides.setdefault(req.providers[0], req.model)
        elif req.model:
            overrides.setdefault(self.policy.default_provider, req.model)
        return overrides

    def _resolve_execution_plan(
        self,
        req: GenerationRequest,
        task_type: str,
    ) -> Tuple[List[RoutedProvider], List[RoutedProvider], str, bool]:
        preferred = [req.provider] if req.provider else list(req.providers)
        model_overrides = self._model_overrides(req)

        if not req.enable_multi_llm and not preferred:
            preferred = [self.policy.default_provider]

        routed = self.router.route(
            task_type,
            preferred=preferred or None,
            model_overrides=model_overrides,
            default_model_override=req.model if len(preferred) == 1 else None,
        )
        fallbacks = self.router.fallbacks(
            task_type,
            exclude=[item.name for item in routed],
            model_overrides=model_overrides,
        )
        strategy = self.router.combination_strategy(task_type, override=req.combine_strategy)
        parallel = self.router.run_in_parallel(task_type, override=req.parallel)

        if preferred or not req.enable_multi_llm:
            parallel = bool(req.parallel) if req.parallel is not None else False
        if strategy == "pipeline" and len(routed) < 2:
            strategy = "best"
        if strategy == "pipeline" or len(routed) <= 1:
            parallel = False

        return routed, fallbacks, strategy, parallel

    def _execute_provider(
        self,
        routed_provider: RoutedProvider,
        messages: List[Dict[str, str]],
        req: GenerationRequest,
    ) -> ProviderExecutionResult:
        started_at = perf_counter()
        self.logger.info(
            "Dispatching provider=%s model=%s",
            routed_provider.name,
            routed_provider.model,
        )
        try:
            text = routed_provider.provider.generate(
                messages=messages,
                model=routed_provider.model,
                temperature=req.temperature,
                max_tokens=req.max_tokens,
            )
            latency_ms = round((perf_counter() - started_at) * 1000, 2)
            if self._is_provider_error(text):
                return ProviderExecutionResult(
                    provider_name=routed_provider.name,
                    model=routed_provider.model,
                    error=(text or "").strip() or "Empty provider response",
                    latency_ms=latency_ms,
                )
            self.logger.info(
                "Provider succeeded provider=%s latency_ms=%.2f",
                routed_provider.name,
                latency_ms,
            )
            return ProviderExecutionResult(
                provider_name=routed_provider.name,
                model=routed_provider.model,
                response=text.strip(),
                latency_ms=latency_ms,
            )
        except Exception as exc:
            latency_ms = round((perf_counter() - started_at) * 1000, 2)
            self.logger.warning(
                "Provider failed provider=%s latency_ms=%.2f error=%s",
                routed_provider.name,
                latency_ms,
                exc,
            )
            return ProviderExecutionResult(
                provider_name=routed_provider.name,
                model=routed_provider.model,
                error=str(exc),
                latency_ms=latency_ms,
            )

    @staticmethod
    def _is_provider_error(text: Optional[str]) -> bool:
        if not text or not text.strip():
            return True
        lowered = text.strip().lower()
        return lowered.startswith("provider api key is missing")

    @staticmethod
    def _sort_results(
        results: Sequence[ProviderExecutionResult],
        routed_providers: Sequence[RoutedProvider],
    ) -> List[ProviderExecutionResult]:
        order = {item.name: index for index, item in enumerate(routed_providers)}
        return sorted(results, key=lambda result: order.get(result.provider_name, len(order)))

    def _execute_sequential(
        self,
        routed_providers: Sequence[RoutedProvider],
        messages: List[Dict[str, str]],
        req: GenerationRequest,
    ) -> Tuple[List[ProviderExecutionResult], List[ProviderExecutionResult]]:
        successes: List[ProviderExecutionResult] = []
        failures: List[ProviderExecutionResult] = []
        for routed_provider in routed_providers:
            result = self._execute_provider(routed_provider, messages, req)
            if result.error:
                failures.append(result)
            else:
                successes.append(result)
        return successes, failures

    def _execute_parallel(
        self,
        routed_providers: Sequence[RoutedProvider],
        messages: List[Dict[str, str]],
        req: GenerationRequest,
    ) -> Tuple[List[ProviderExecutionResult], List[ProviderExecutionResult]]:
        if not routed_providers:
            return [], []

        successes: List[ProviderExecutionResult] = []
        failures: List[ProviderExecutionResult] = []
        max_workers = min(len(routed_providers), self.policy.max_parallel_providers)
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_map = {
                executor.submit(self._execute_provider, routed_provider, messages, req): routed_provider
                for routed_provider in routed_providers
            }
            for future in as_completed(future_map):
                result = future.result()
                if result.error:
                    failures.append(result)
                else:
                    successes.append(result)
        return self._sort_results(successes, routed_providers), self._sort_results(failures, routed_providers)

    @staticmethod
    def _pipeline_messages(
        base_messages: List[Dict[str, str]],
        prior_response: str,
        step_index: int,
    ) -> List[Dict[str, str]]:
        instructions = [
            "Create the initial draft. Focus on correctness and useful substance.",
            "Refine the previous draft. Improve accuracy, structure, and completeness while preserving intent.",
            "Polish the response for clarity, concision, and final delivery. Return only the final answer.",
        ]
        instruction = instructions[min(step_index, len(instructions) - 1)]
        return [
            *base_messages,
            {"role": "assistant", "content": prior_response},
            {"role": "user", "content": instruction},
        ]

    def _execute_pipeline(
        self,
        routed_providers: Sequence[RoutedProvider],
        messages: List[Dict[str, str]],
        req: GenerationRequest,
    ) -> Tuple[List[ProviderExecutionResult], List[ProviderExecutionResult]]:
        successes: List[ProviderExecutionResult] = []
        failures: List[ProviderExecutionResult] = []
        current_messages = list(messages)

        for step_index, routed_provider in enumerate(routed_providers):
            result = self._execute_provider(routed_provider, current_messages, req)
            if result.error:
                failures.append(result)
                continue
            successes.append(result)
            current_messages = self._pipeline_messages(messages, result.response, step_index + 1)

        return successes, failures

    def _attempt_fallbacks(
        self,
        routed_providers: Sequence[RoutedProvider],
        messages: List[Dict[str, str]],
        req: GenerationRequest,
    ) -> Tuple[List[ProviderExecutionResult], List[ProviderExecutionResult]]:
        if not routed_providers:
            return [], []
        self.logger.info("Primary route failed, trying fallback providers")
        return self._execute_sequential(routed_providers, messages, req)

    @staticmethod
    def _merge_responses(responses: Sequence[str]) -> str:
        blocks: List[str] = []
        seen = set()
        for response in responses:
            for block in [part.strip() for part in response.split("\n\n") if part.strip()]:
                normalized = " ".join(block.lower().split())
                if normalized in seen:
                    continue
                seen.add(normalized)
                blocks.append(block)
        return "\n\n".join(blocks) if blocks else ""

    def _score_response(self, response: str, task_type: str) -> int:
        cleaned = response.strip()
        if not cleaned:
            return -10000

        score = min(len(cleaned), 1200)
        if task_type == "coding" and "```" in cleaned:
            score += 250
        if task_type in {"summarization", "rag"} and any(
            marker in cleaned.lower() for marker in ("summary", "key points", "overview")
        ):
            score += 80
        if cleaned.count("\n") >= 2:
            score += 40
        if cleaned.endswith((".", "!", "?", ":")):
            score += 20
        if cleaned.lower().startswith("sorry"):
            score -= 50
        return score

    def combine_responses(
        self,
        responses: List[str],
        strategy: str = "merge",
        task_type: str = "general",
    ) -> str:
        cleaned = [response.strip() for response in responses if response and response.strip()]
        if not cleaned:
            return "All configured providers failed to generate a response."
        if strategy == "pipeline":
            return cleaned[-1]
        if strategy == "best":
            return max(cleaned, key=lambda response: self._score_response(response, task_type))
        return self._merge_responses(cleaned)

    def _execute_multi_llm(
        self,
        routed_providers: Sequence[RoutedProvider],
        fallback_providers: Sequence[RoutedProvider],
        messages: List[Dict[str, str]],
        req: GenerationRequest,
        strategy: str,
        parallel: bool,
    ) -> Tuple[List[ProviderExecutionResult], List[ProviderExecutionResult]]:
        if strategy == "pipeline":
            primary_successes, primary_failures = self._execute_pipeline(routed_providers, messages, req)
        elif parallel:
            primary_successes, primary_failures = self._execute_parallel(routed_providers, messages, req)
        else:
            primary_successes, primary_failures = self._execute_sequential(routed_providers, messages, req)

        if primary_successes:
            return primary_successes, primary_failures

        fallback_successes, fallback_failures = self._attempt_fallbacks(fallback_providers, messages, req)
        return fallback_successes, primary_failures + fallback_failures

    def generate(self, req: GenerationRequest) -> Dict[str, Any]:
        task_type = self._detect_task(req)
        messages = self._build_messages(req)
        routed_providers, fallback_providers, strategy, parallel = self._resolve_execution_plan(req, task_type)
        successes, failures = self._execute_multi_llm(
            routed_providers,
            fallback_providers,
            messages,
            req,
            strategy,
            parallel,
        )

        if not successes:
            return {
                "success": False,
                "provider": None,
                "model": None,
                "providers": [],
                "models": {},
                "task_type": task_type,
                "combine_strategy": strategy,
                "parallel": parallel,
                "response": "All configured LLM providers failed to generate a response.",
                "provider_results": [],
                "failures": [asdict(result) for result in failures],
            }

        combined = self.combine_responses(
            [result.response for result in successes],
            strategy=strategy,
            task_type=task_type,
        )
        return {
            "success": True,
            "provider": successes[0].provider_name,
            "model": successes[0].model,
            "providers": [result.provider_name for result in successes],
            "models": {result.provider_name: result.model for result in successes},
            "task_type": task_type,
            "combine_strategy": strategy,
            "parallel": parallel,
            "response": combined,
            "provider_results": [asdict(result) for result in successes],
            "failures": [asdict(result) for result in failures],
        }

    async def generate_stream(
        self,
        req: GenerationRequest,
        on_token: Callable[[str], None],
    ) -> Dict[str, Any]:
        result = await asyncio.to_thread(self.generate, req)
        result["response"] = await self.streamer.stream_text(result.get("response", ""), on_token=on_token)
        return result

    def generate_stream_sync(
        self,
        req: GenerationRequest,
        on_token: Callable[[str], None],
    ) -> Dict[str, Any]:
        return asyncio.run(self.generate_stream(req=req, on_token=on_token))

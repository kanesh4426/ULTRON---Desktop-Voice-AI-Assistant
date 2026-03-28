import asyncio
import json
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

from app.agents.planner import AgentPlanner
from app.llm.streaming.response_streamer import ResponseStreamer
from app.tools.executor import ToolExecutor
from app.llm.providers import GeminiProvider, GroqProvider, HuggingFaceProvider, OpenRouterProvider
from app.models.generation_request import GenerationRequest
from app.prompts.template_engine import PromptTemplateEngine
from app.rag import DocumentLoader, EmbeddingModel, Retriever, TextChunker, VectorStore
from app.tools.registry import SystemToolRegistry
from app.utils.config import AssistantConfig
from app.utils.logger import get_logger


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
        if model:
            self.config.model = model

    def ingest_documents(self, directory_path: str) -> Dict[str, Any]:
        docs = self.doc_loader.load_from_directory(directory_path, recursive=True)
        chunks = self.chunker.chunk_documents(docs)
        embeddings = self.embedding_model.embed([c["chunk"] for c in chunks])
        metadata = [{"path": c["path"], "chunk": c["chunk"]} for c in chunks]
        self.vector_store.add(embeddings, metadata)
        return {"success": True, "documents": len(docs), "chunks": len(chunks)}

    def _build_messages(self, req: GenerationRequest) -> List[Dict[str, str]]:
        query = req.user_input
        context_blocks = []
        if req.use_rag:
            hits = self.retriever.retrieve(query, top_k=req.rag_top_k or self.config.rag_top_k)
            for h in hits:
                context_blocks.append(f"Source: {h.get('path')}\n{h.get('chunk')}")

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

    def generate(self, req: GenerationRequest) -> Dict[str, Any]:
        provider_name = req.provider or self.config.provider
        model = req.model or self.config.model
        provider = self.providers[provider_name]
        messages = self._build_messages(req)
        text = provider.generate(
            messages=messages,
            model=model,
            temperature=req.temperature,
            max_tokens=req.max_tokens,
        )
        return {"success": True, "provider": provider_name, "model": model, "response": text}

    async def generate_stream(
        self,
        req: GenerationRequest,
        on_token: Callable[[str], None],
    ) -> Dict[str, Any]:
        provider_name = req.provider or self.config.provider
        model = req.model or self.config.model
        provider = self.providers[provider_name]
        messages = self._build_messages(req)
        text = await self.streamer.stream_provider(
            provider=provider,
            messages=messages,
            model=model,
            on_token=on_token,
            temperature=req.temperature,
            max_tokens=req.max_tokens,
        )
        return {"success": True, "provider": provider_name, "model": model, "response": text}

    def generate_stream_sync(
        self,
        req: GenerationRequest,
        on_token: Callable[[str], None],
    ) -> Dict[str, Any]:
        return asyncio.run(self.generate_stream(req=req, on_token=on_token))

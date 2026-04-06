from __future__ import annotations

from pathlib import Path
from typing import Dict, List, Optional, Sequence

from app.llm.policies import ModelPolicy
from app.llm.providers import GeminiProvider, GroqProvider, HuggingFaceProvider, OpenRouterProvider
from app.llm.router import LLMRouter, RoutedProvider
from app.rag import DocumentLoader, EmbeddingModel, Retriever, TextChunker, VectorStore
from app.utils.config import AssistantConfig

from .editing import DeltaEditor
from .formatting import StructuredMarkdownFormatter
from .grounding import DocumentGrounder, RetrieverGrounder, format_grounding_block
from .models import (
    ContentGenerationRequest,
    ContentGenerationResult,
    DeltaUpdate,
    GroundingHit,
    StyleDNA,
)
from .storage import ContentArtifactStore
from .style_dna import SessionStyleRegistry, build_style_instruction


class ContentGenerationEngine:
    def __init__(
        self,
        config: Optional[AssistantConfig] = None,
        *,
        providers: Optional[Dict[str, object]] = None,
        grounder: Optional[DocumentGrounder] = None,
        formatter: Optional[StructuredMarkdownFormatter] = None,
        delta_editor: Optional[DeltaEditor] = None,
        style_registry: Optional[SessionStyleRegistry] = None,
        store: Optional[ContentArtifactStore] = None,
    ) -> None:
        self.config = config or AssistantConfig.from_env()
        self.providers = providers or self._build_default_providers(self.config)
        self.policy = ModelPolicy(
            default_provider=self.config.provider,
            default_model=self.config.model,
        )
        self.router = LLMRouter(self.providers, policy=self.policy)

        self.doc_loader = DocumentLoader()
        self.chunker = TextChunker()
        self.embedding_model: Optional[EmbeddingModel] = None
        self.vector_store: Optional[VectorStore] = None
        self.retriever: Optional[Retriever] = None
        self.grounder = grounder
        if self.grounder is None:
            self._ensure_rag_components()
            self.grounder = RetrieverGrounder(self.retriever)

        self.formatter = formatter or StructuredMarkdownFormatter()
        self.delta_editor = delta_editor or DeltaEditor()
        self.style_registry = style_registry or SessionStyleRegistry()
        default_store_dir = Path(self.config.workspace_root) / "data" / "content"
        self.store = store or ContentArtifactStore(base_dir=str(default_store_dir))
        self._session_outputs: Dict[str, str] = {}

    def ingest_documents(self, directory_path: str) -> Dict[str, int | bool]:
        self._ensure_rag_components()
        docs = self.doc_loader.load_from_directory(directory_path, recursive=True)
        chunks = self.chunker.chunk_documents(docs)
        embeddings = self.embedding_model.embed([chunk["chunk"] for chunk in chunks])
        metadata = [{"path": chunk["path"], "chunk": chunk["chunk"]} for chunk in chunks]
        self.vector_store.add(embeddings, metadata)
        return {"success": True, "documents": len(docs), "chunks": len(chunks)}

    def validate_output(self, content: str) -> List[str]:
        return self.formatter.validate(content)

    def last_output_for_session(self, session_id: str) -> str:
        return self._session_outputs.get(session_id, "")

    def generate(self, request: ContentGenerationRequest) -> ContentGenerationResult:
        session_id = request.session_id or "default"
        style = self.style_registry.resolve(session_id, request.style_dna)
        grounding_hits = self._resolve_grounding(request)
        messages = self._build_messages(request, style, grounding_hits)

        provider_name: Optional[str] = None
        model_name: Optional[str] = None
        raw_content = ""
        failures: List[Dict[str, str]] = []
        attempts = 0

        try:
            for routed in self._candidate_providers(request):
                attempts += 1
                text = routed.provider.generate(
                    messages=messages,
                    model=routed.model,
                    temperature=request.temperature,
                    max_tokens=request.max_tokens,
                )
                if self._is_provider_error(text):
                    failures.append(
                        {
                            "provider": routed.name,
                            "model": routed.model,
                            "error": (text or "").strip() or "Empty response",
                        }
                    )
                    continue
                provider_name = routed.name
                model_name = routed.model
                raw_content = text.strip()
                break
        except Exception as exc:
            failures.append(
                {
                    "provider": provider_name or "unknown",
                    "model": model_name or "unknown",
                    "error": str(exc),
                }
            )

        if not raw_content:
            return ContentGenerationResult(
                success=False,
                session_id=session_id,
                content_type=request.content_type,
                style_dna=style,
                grounding_hits=grounding_hits,
                metadata={"failures": failures, **request.metadata},
                attempts=attempts,
                error="All configured content providers failed to generate a response.",
            )

        formatted = self.formatter.format(
            prompt=request.user_input,
            raw_content=raw_content,
            title=request.title,
            content_type=request.content_type,
            style_dna=style,
            grounding_hits=grounding_hits,
            session_id=session_id,
            provider=provider_name,
            model=model_name,
        )
        quality_issues = self.formatter.validate(formatted)

        filepath = None
        if request.persist_output:
            filepath = self.store.save(
                content=formatted,
                prompt=request.user_input,
                content_type=request.content_type,
                metadata={
                    "generated_at": request.metadata.get("generated_at", ""),
                    "session_id": session_id,
                    "provider": provider_name or "",
                    "model": model_name or "",
                },
                output_dir=request.output_dir,
            )

        self._session_outputs[session_id] = formatted
        return ContentGenerationResult(
            success=True,
            content=formatted,
            raw_content=raw_content,
            provider=provider_name,
            model=model_name,
            session_id=session_id,
            content_type=request.content_type,
            style_dna=style,
            grounding_hits=grounding_hits,
            quality_issues=quality_issues,
            metadata={"failures": failures, **request.metadata},
            filepath=filepath,
            attempts=max(attempts, 1),
        )

    def apply_delta(
        self,
        *,
        session_id: str,
        delta: DeltaUpdate | Sequence[DeltaUpdate],
        original_content: Optional[str] = None,
        content_type: str = "article",
        persist_output: bool = False,
        output_dir: Optional[str] = None,
        metadata: Optional[Dict[str, str]] = None,
    ) -> ContentGenerationResult:
        base_content = original_content or self._session_outputs.get(session_id, "")
        style = self.style_registry.get(session_id)
        if not base_content:
            return ContentGenerationResult(
                success=False,
                session_id=session_id,
                content_type=content_type,
                style_dna=style,
                attempts=1,
                error="No base content was available for delta editing.",
            )

        try:
            updated = self.delta_editor.apply(base_content, delta)
        except Exception as exc:
            return ContentGenerationResult(
                success=False,
                session_id=session_id,
                content_type=content_type,
                style_dna=style,
                attempts=1,
                error=str(exc),
            )

        quality_issues = self.formatter.validate(updated)
        filepath = None
        if persist_output:
            filepath = self.store.save(
                content=updated,
                prompt="delta-update",
                content_type=content_type,
                metadata=metadata,
                output_dir=output_dir,
            )

        self._session_outputs[session_id] = updated
        return ContentGenerationResult(
            success=True,
            content=updated,
            raw_content=updated,
            provider="delta-editor",
            model="inline-update",
            session_id=session_id,
            content_type=content_type,
            style_dna=style,
            quality_issues=quality_issues,
            metadata=metadata or {},
            filepath=filepath,
            attempts=1,
            updated_from_delta=True,
        )

    def _candidate_providers(self, request: ContentGenerationRequest) -> List[RoutedProvider]:
        preferred = [request.provider] if request.provider else None
        model_overrides: Dict[str, str] = {}
        if request.provider and request.model:
            model_overrides[request.provider] = request.model
        routed = self.router.route(
            "general",
            preferred=preferred,
            model_overrides=model_overrides or None,
            default_model_override=request.model,
        )
        fallbacks = self.router.fallbacks(
            "general",
            exclude=[item.name for item in routed],
            model_overrides=model_overrides or None,
        )
        return [*routed, *fallbacks]

    def _resolve_grounding(self, request: ContentGenerationRequest) -> List[GroundingHit]:
        if request.document_hits:
            hits: List[GroundingHit] = []
            for item in request.document_hits:
                hits.append(item if isinstance(item, GroundingHit) else GroundingHit.from_mapping(item))
            return hits
        if not request.use_rag:
            return []
        query = request.document_query or request.user_input
        return self.grounder.retrieve(query, top_k=request.rag_top_k or self.config.rag_top_k)

    def _build_messages(
        self,
        request: ContentGenerationRequest,
        style_dna: StyleDNA,
        grounding_hits: Sequence[GroundingHit],
    ) -> List[Dict[str, str]]:
        system_parts = [
            "You are a high-fidelity content generation engine embedded in a software product.",
            "Maintain the same style DNA across the session unless a new override is supplied.",
            "Return only the editorial body. The application will add markdown framing, tables, and callouts after generation.",
            "Use concrete claims, avoid filler, and keep the response ready for structured markdown rendering.",
            build_style_instruction(style_dna),
        ]
        if grounding_hits:
            system_parts.append(
                "Grounded source material:\n" + format_grounding_block(grounding_hits)
            )
            system_parts.append(
                "When grounded evidence is present, make factual claims only from that evidence."
            )

        prior_output = self._session_outputs.get(request.session_id)
        if prior_output:
            system_parts.append(
                "Session continuity excerpt:\n" + self._continuity_excerpt(prior_output)
            )

        user_parts = [
            f"Content type: {request.content_type}",
            f"User request: {request.user_input}",
        ]
        if request.title:
            user_parts.append(f"Working title: {request.title}")
        if request.target_sections:
            user_parts.append(
                "Requested sections: " + ", ".join(request.target_sections)
            )
        if request.metadata.get("additional_instructions"):
            user_parts.append(str(request.metadata["additional_instructions"]))

        return [
            {"role": "system", "content": "\n\n".join(system_parts)},
            {"role": "user", "content": "\n".join(user_parts)},
        ]

    @staticmethod
    def _continuity_excerpt(content: str, limit: int = 500) -> str:
        text = " ".join((content or "").split())
        if len(text) <= limit:
            return text
        return text[: limit - 3].rstrip() + "..."

    @staticmethod
    def _is_provider_error(text: Optional[str]) -> bool:
        if not text or not text.strip():
            return True
        lowered = text.strip().lower()
        return lowered.startswith("provider api key is missing")

    @staticmethod
    def _build_default_providers(config: AssistantConfig) -> Dict[str, object]:
        return {
            "groq": GroqProvider(config.groq_api_key, timeout=config.request_timeout),
            "gemini": GeminiProvider(config.gemini_api_key, timeout=config.request_timeout),
            "huggingface": HuggingFaceProvider(config.huggingface_api_key, timeout=config.request_timeout),
            "openrouter": OpenRouterProvider(config.openrouter_api_key, timeout=config.request_timeout),
        }

    def _ensure_rag_components(self) -> None:
        if self.embedding_model is None:
            self.embedding_model = EmbeddingModel()
        if self.vector_store is None:
            self.vector_store = VectorStore(self.config.rag_store_path)
        if self.retriever is None:
            self.retriever = Retriever(self.embedding_model, self.vector_store)

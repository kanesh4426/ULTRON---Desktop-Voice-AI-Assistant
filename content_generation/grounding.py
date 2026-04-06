from __future__ import annotations

from typing import List, Protocol, Sequence

from app.rag.retriever import Retriever

from .models import GroundingHit


class DocumentGrounder(Protocol):
    def retrieve(self, query: str, top_k: int = 4) -> List[GroundingHit]:
        ...


class RetrieverGrounder:
    def __init__(self, retriever: Retriever) -> None:
        self.retriever = retriever

    def retrieve(self, query: str, top_k: int = 4) -> List[GroundingHit]:
        return [
            GroundingHit.from_mapping(hit)
            for hit in self.retriever.retrieve(query, top_k=top_k)
        ]


class StaticGrounder:
    def __init__(self, hits: Sequence[GroundingHit | dict]) -> None:
        self.hits = [
            hit if isinstance(hit, GroundingHit) else GroundingHit.from_mapping(hit)
            for hit in hits
        ]

    def retrieve(self, query: str, top_k: int = 4) -> List[GroundingHit]:
        return list(self.hits[:top_k])


def format_grounding_block(hits: Sequence[GroundingHit]) -> str:
    if not hits:
        return "No grounded context supplied."
    parts = []
    for hit in hits:
        parts.append(f"Source: {hit.path}\nExcerpt: {hit.excerpt}")
    return "\n\n".join(parts)

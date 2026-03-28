from __future__ import annotations

from typing import Any, Dict, List

from app.rag.vector_store import VectorStore


class VectorMemory:
    """
    Thin wrapper around VectorStore for long-term memory.
    """

    def __init__(self, store: VectorStore) -> None:
        self.store = store

    def add(self, embeddings: List[List[float]], metadata: List[Dict[str, Any]]) -> None:
        self.store.add(embeddings, metadata)

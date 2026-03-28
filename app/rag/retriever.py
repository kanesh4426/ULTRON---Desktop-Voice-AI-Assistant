from typing import Dict, List

from .embedding_model import EmbeddingModel
from .vector_store import VectorStore


class Retriever:
    def __init__(self, embedding_model: EmbeddingModel, vector_store: VectorStore):
        self.embedding_model = embedding_model
        self.vector_store = vector_store

    def retrieve(self, query: str, top_k: int = 4) -> List[Dict[str, str]]:
        emb = self.embedding_model.embed([query])[0]
        return self.vector_store.search(emb, top_k=top_k)


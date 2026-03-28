import hashlib
from typing import List


class EmbeddingModel:
    """
    Sentence-transformers optional; deterministic hash fallback otherwise.
    """

    def __init__(self, model_name: str = "all-MiniLM-L6-v2"):
        self.model_name = model_name
        self._model = None
        try:
            from sentence_transformers import SentenceTransformer

            self._model = SentenceTransformer(model_name)
        except Exception:
            self._model = None

    def embed(self, texts: List[str]) -> List[List[float]]:
        if self._model is not None:
            vectors = self._model.encode(texts, normalize_embeddings=True)
            return [v.tolist() for v in vectors]
        return [self._hash_embed(t) for t in texts]

    @staticmethod
    def _hash_embed(text: str, size: int = 384) -> List[float]:
        raw = hashlib.sha256(text.encode("utf-8")).digest()
        vals = [raw[i % len(raw)] / 255.0 for i in range(size)]
        norm = sum(v * v for v in vals) ** 0.5 or 1.0
        return [v / norm for v in vals]


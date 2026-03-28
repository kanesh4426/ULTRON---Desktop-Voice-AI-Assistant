import json
from pathlib import Path
from typing import Dict, List, Tuple


class VectorStore:
    def __init__(self, store_path: str):
        self.store_path = Path(store_path)
        self.store_path.mkdir(parents=True, exist_ok=True)
        self.index_path = self.store_path / "index.faiss"
        self.meta_path = self.store_path / "metadata.json"
        self._faiss = None
        self._index = None
        self._metadata: List[Dict[str, str]] = []
        self._embeddings: List[List[float]] = []

        try:
            import faiss

            self._faiss = faiss
        except Exception:
            self._faiss = None

        self._load()

    def add(self, embeddings: List[List[float]], metadata: List[Dict[str, str]]) -> None:
        if not embeddings:
            return
        self._metadata.extend(metadata)
        if self._faiss is not None:
            import numpy as np

            vec = np.array(embeddings, dtype="float32")
            if self._index is None:
                self._index = self._faiss.IndexFlatIP(vec.shape[1])
            self._index.add(vec)
        else:
            self._embeddings.extend(embeddings)
        self._save()

    def search(self, query_embedding: List[float], top_k: int = 4) -> List[Dict[str, str]]:
        if not self._metadata:
            return []
        if self._faiss is not None and self._index is not None:
            import numpy as np

            q = np.array([query_embedding], dtype="float32")
            distances, indices = self._index.search(q, top_k)
            results: List[Dict[str, str]] = []
            for idx in indices[0]:
                if idx < 0 or idx >= len(self._metadata):
                    continue
                results.append(self._metadata[idx])
            return results
        # fallback cosine-like dot product for in-memory list
        scored: List[Tuple[float, int]] = []
        for i, emb in enumerate(self._embeddings):
            score = sum(a * b for a, b in zip(query_embedding, emb))
            scored.append((score, i))
        scored.sort(reverse=True, key=lambda x: x[0])
        return [self._metadata[i] for _, i in scored[:top_k]]

    def _save(self) -> None:
        self.meta_path.write_text(json.dumps(self._metadata, ensure_ascii=False, indent=2), encoding="utf-8")
        if self._faiss is not None and self._index is not None:
            self._faiss.write_index(self._index, str(self.index_path))
        else:
            (self.store_path / "embeddings.json").write_text(
                json.dumps(self._embeddings, ensure_ascii=False),
                encoding="utf-8",
            )

    def _load(self) -> None:
        if self.meta_path.exists():
            try:
                self._metadata = json.loads(self.meta_path.read_text(encoding="utf-8"))
            except Exception:
                self._metadata = []

        if self._faiss is not None and self.index_path.exists():
            try:
                self._index = self._faiss.read_index(str(self.index_path))
            except Exception:
                self._index = None
        else:
            emb_path = self.store_path / "embeddings.json"
            if emb_path.exists():
                try:
                    self._embeddings = json.loads(emb_path.read_text(encoding="utf-8"))
                except Exception:
                    self._embeddings = []


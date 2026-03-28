from typing import Dict, List


class TextChunker:
    def __init__(self, chunk_size: int = 600, overlap: int = 100):
        self.chunk_size = chunk_size
        self.overlap = overlap

    def chunk_documents(self, docs: List[Dict[str, str]]) -> List[Dict[str, str]]:
        chunks: List[Dict[str, str]] = []
        for doc in docs:
            text = doc.get("content", "")
            path = doc.get("path", "")
            start = 0
            while start < len(text):
                end = min(start + self.chunk_size, len(text))
                chunk = text[start:end]
                chunks.append({"path": path, "chunk": chunk})
                if end >= len(text):
                    break
                start = end - self.overlap
        return chunks


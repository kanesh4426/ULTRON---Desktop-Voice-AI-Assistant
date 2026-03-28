from pathlib import Path
from typing import Dict, List


class DocumentLoader:
    SUPPORTED_SUFFIXES = {".txt", ".md", ".py", ".json", ".csv", ".log"}

    def load_from_directory(self, root: str, recursive: bool = True) -> List[Dict[str, str]]:
        base = Path(root).expanduser().resolve()
        iterator = base.rglob("*") if recursive else base.iterdir()
        docs: List[Dict[str, str]] = []
        for p in iterator:
            if not p.is_file() or p.suffix.lower() not in self.SUPPORTED_SUFFIXES:
                continue
            try:
                docs.append({"path": str(p), "content": p.read_text(encoding="utf-8", errors="ignore")})
            except Exception:
                continue
        return docs


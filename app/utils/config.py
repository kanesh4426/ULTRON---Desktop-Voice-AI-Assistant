import os
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Optional


def _load_env_file(env_path: Path) -> Dict[str, str]:
    output: Dict[str, str] = {}
    if not env_path.exists():
        return output
    for raw in env_path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        output[k.strip()] = v.strip().strip('"').strip("'")
    return output


@dataclass
class AssistantConfig:
    provider: str = "groq"
    model: str = "llama-3.3-70b-versatile"
    workspace_root: str = "."
    rag_store_path: str = "data/rag_index"
    rag_top_k: int = 4
    request_timeout: float = 60.0

    groq_api_key: Optional[str] = None
    gemini_api_key: Optional[str] = None
    huggingface_api_key: Optional[str] = None
    openrouter_api_key: Optional[str] = None

    @staticmethod
    def from_env(project_root: Optional[str] = None) -> "AssistantConfig":
        base = Path(project_root or ".").resolve()
        env = _load_env_file(base / ".env")
        get = lambda key, default=None: os.getenv(key) or env.get(key, default)
        return AssistantConfig(
            provider=get("ASSISTANT_PROVIDER", "groq"),
            model=get("ASSISTANT_MODEL", "llama-3.3-70b-versatile"),
            workspace_root=get("ASSISTANT_WORKSPACE_ROOT", str(base)),
            rag_store_path=get("ASSISTANT_RAG_STORE_PATH", str(base / "data" / "rag_index")),
            rag_top_k=int(get("ASSISTANT_RAG_TOP_K", "4")),
            request_timeout=float(get("ASSISTANT_TIMEOUT", "60")),
            groq_api_key=get("GROQ_API_KEY"),
            gemini_api_key=get("GEMINI_API_KEY"),
            huggingface_api_key=get("HUGGINGFACE_API_KEY"),
            openrouter_api_key=get("OPENROUTER_API_KEY"),
        )

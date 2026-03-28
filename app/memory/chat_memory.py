from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List


@dataclass
class ChatMemory:
    """
    In-memory chat history. Replace with persistent storage in production.
    """

    messages: List[Dict[str, str]] = field(default_factory=list)

    def append(self, role: str, content: str) -> None:
        self.messages.append({"role": role, "content": content})

    def tail(self, limit: int = 20) -> List[Dict[str, str]]:
        return self.messages[-limit:]

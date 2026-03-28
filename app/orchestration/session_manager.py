from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List


@dataclass
class Session:
    session_id: str
    messages: List[Dict[str, str]] = field(default_factory=list)


class SessionManager:
    """
    Manages in-memory sessions. Persisting sessions should be delegated to services.
    """

    def __init__(self) -> None:
        self._sessions: Dict[str, Session] = {}

    def get_or_create(self, session_id: str) -> Session:
        if session_id not in self._sessions:
            self._sessions[session_id] = Session(session_id=session_id)
        return self._sessions[session_id]

    def clear(self, session_id: str) -> None:
        if session_id in self._sessions:
            del self._sessions[session_id]

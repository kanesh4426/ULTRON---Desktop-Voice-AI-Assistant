from __future__ import annotations


class MemoryStore:
    """
    Placeholder abstraction for persistent memory stores (SQLite, Redis, etc).
    """

    def __init__(self, uri: str = "") -> None:
        self.uri = uri

from __future__ import annotations


class SandboxPolicy:
    """
    Placeholder for sandbox rules and enforcement.
    """

    def __init__(self, allow_network: bool = False, allow_system: bool = False) -> None:
        self.allow_network = allow_network
        self.allow_system = allow_system

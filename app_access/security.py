from __future__ import annotations

from typing import Iterable, Optional, Sequence


class DangerousOperationError(PermissionError):
    pass


class CommandGuard:
    """
    Lightweight safety checks for system command execution.
    """

    def __init__(
        self,
        require_confirmation: bool = True,
        dangerous_commands: Optional[Iterable[str]] = None,
    ) -> None:
        self.require_confirmation = require_confirmation
        self.confirmation_required = require_confirmation
        self.dangerous_commands = {c.lower() for c in (dangerous_commands or _default_dangerous_commands())}

    def is_dangerous(self, tokens: Sequence[str], raw: Optional[str] = None) -> bool:
        if not tokens:
            return False
        head = tokens[0].lower()
        if head in self.dangerous_commands:
            return True
        if raw:
            # Shell metacharacters and redirections are riskier.
            for token in ("&&", "||", "|", ">", "<"):
                if token in raw:
                    return True
        return False

    def ensure_confirmed(self, confirm: bool, operation: str) -> None:
       if self.confirmation_required and not confirm:
             raise DangerousOperationError(f"{operation} requires confirmation (set confirm=True).")


def _default_dangerous_commands() -> list[str]:
    return [
        "rm",
        "rmdir",
        "del",
        "erase",
        "format",
        "mkfs",
        "dd",
        "shutdown",
        "reboot",
        "poweroff",
        "kill",
        "taskkill",
    ]

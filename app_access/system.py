from __future__ import annotations

import os
import shlex
import subprocess
from typing import Any, Dict, Optional, Sequence, Union

from app.utils.logger import get_logger

from .security import CommandGuard


class SystemCommandRunner:
    """
    Safer system command runner with confirmation and timeout handling.
    """

    def __init__(
        self,
        allow_shell: bool = False,
        guard: Optional[CommandGuard] = None,
    ) -> None:
        self.allow_shell = allow_shell
        self.guard = guard or CommandGuard()
        self.logger = get_logger("assistant.system")

    def run(
        self,
        command: Union[str, Sequence[str]],
        *,
        timeout_sec: int = 10,
        allow_shell: Optional[bool] = None,
        confirm: bool = False,
        cwd: Optional[str] = None,
        env: Optional[Dict[str, str]] = None,
    ) -> Dict[str, Any]:
        use_shell = self.allow_shell if allow_shell is None else allow_shell
        raw = ""
        tokens: list[str] = []

        if isinstance(command, str):
            raw = command.strip()
            if not raw:
                return {"success": False, "error": "Empty command"}
            if use_shell:
                tokens = _split_tokens(raw)
                cmd = raw
            else:
                tokens = _split_tokens(raw)
                cmd = tokens
        else:
            tokens = [str(t) for t in command]
            raw = " ".join(tokens)
            cmd = tokens

        if not tokens:
            return {"success": False, "error": "Command parsing failed"}

        if self.guard and self.guard.is_dangerous(tokens, raw):
            try:
                self.guard.ensure_confirmed(confirm, "run_command")
            except Exception as exc:
                return {"success": False, "error": str(exc)}

        try:
            self.logger.info("system_command_start command=%s", raw)
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=timeout_sec,
                shell=use_shell,
                cwd=cwd,
                env=env,
            )
            payload = {
                "success": result.returncode == 0,
                "stdout": result.stdout,
                "stderr": result.stderr,
                "returncode": result.returncode,
            }
            self.logger.info("system_command_end command=%s rc=%s", raw, result.returncode)
            return payload
        except subprocess.TimeoutExpired:
            self.logger.warning("system_command_timeout command=%s timeout=%s", raw, timeout_sec)
            return {"success": False, "error": f"Execution timed out after {timeout_sec}s"}
        except Exception as exc:
            self.logger.exception("system_command_failed command=%s", raw)
            return {"success": False, "error": f"Execution failed: {exc}"}


def _split_tokens(command: str) -> list[str]:
    if os.name == "nt":
        return shlex.split(command, posix=False)
    return shlex.split(command, posix=True)

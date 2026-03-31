from pathlib import Path
from typing import Optional


class WorkspaceSecurityError(PermissionError):
    pass


class WorkspaceGuard:
    """
    Restricts all operations to a workspace directory and prevents traversal.
    """

    def __init__(self, workspace_root: str):
        root = Path(workspace_root).expanduser().resolve()
        self.workspace_root = root

    def resolve_path(self, raw_path: str, must_exist: bool = False) -> Path:
        candidate = Path(raw_path).expanduser()
        if not candidate.is_absolute():
            candidate = self.workspace_root / candidate

        resolved = candidate.resolve(strict=False)
        self._ensure_inside_workspace(resolved)

        if must_exist and not resolved.exists():
            raise FileNotFoundError(f"Path does not exist: {raw_path}")
        return resolved

    def _ensure_inside_workspace(self, path: Path) -> None:
        try:
            path.relative_to(self.workspace_root)
        except ValueError as exc:
            raise WorkspaceSecurityError(
                f"Path is outside workspace: {path} (workspace: {self.workspace_root})"
            ) from exc


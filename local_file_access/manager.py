import json
import logging
import mimetypes
import shutil
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from .history import OperationHistory
from .models import FileMetadata, OperationRecord
from .security import WorkspaceGuard, WorkspaceSecurityError


@dataclass
class FileManagerConfig:
    workspace_root: str
    max_read_bytes: int = 5 * 1024 * 1024
    require_delete_confirmation: bool = True
    log_file: Optional[str] = None
    history_file: Optional[str] = None


class FileManager:
    def __init__(self, config: FileManagerConfig):
        self.config = config
        self.guard = WorkspaceGuard(config.workspace_root)

        workspace = Path(config.workspace_root).expanduser().resolve()
        self._system_dir = workspace / ".ultron_file_access"

        self.log_file = Path(config.log_file) if config.log_file else self._system_dir / "operations.log"
        self.history_file = Path(config.history_file) if config.history_file else self._system_dir / "history.jsonl"

        self.logger = logging.getLogger(f"{__name__}.FileManager")
        self.logger.setLevel(logging.INFO)
        self._logger_initialized = False
        self._history = None

    @property
    def history(self):
        if self._history is None:
            self._system_dir.mkdir(parents=True, exist_ok=True)
            self._history = OperationHistory(self.history_file)
        return self._history

    def _ensure_logger(self):
        if not self._logger_initialized:
            if not self.logger.handlers:
                self.log_file.parent.mkdir(parents=True, exist_ok=True)
                fh = logging.FileHandler(self.log_file, encoding="utf-8")
                fh.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
                self.logger.addHandler(fh)
            self._logger_initialized = True

    def create_file(self, file_path: str, content: str = "", overwrite: bool = False) -> Dict[str, Any]:
        return self._run("create_file", lambda: self._create_file(file_path, content, overwrite), file_path)

    def read_file(self, file_path: str, encoding: str = "utf-8") -> Dict[str, Any]:
        return self._run("read_file", lambda: self._read_file(file_path, encoding), file_path)

    def write_file(self, file_path: str, content: str, encoding: str = "utf-8") -> Dict[str, Any]:
        return self._run("write_file", lambda: self._write_file(file_path, content, encoding, append=False), file_path)

    def append_file(self, file_path: str, content: str, encoding: str = "utf-8") -> Dict[str, Any]:
        return self._run("append_file", lambda: self._write_file(file_path, content, encoding, append=True), file_path)

    def delete_file(self, file_path: str, confirm: bool = False) -> Dict[str, Any]:
        return self._run("delete_file", lambda: self._delete_file(file_path, confirm), file_path)

    def rename_file(self, source_path: str, new_name: str) -> Dict[str, Any]:
        return self._run("rename_file", lambda: self._rename_file(source_path, new_name), source_path, new_name)

    def move_file(self, source_path: str, destination_path: str) -> Dict[str, Any]:
        return self._run("move_file", lambda: self._move_file(source_path, destination_path), source_path, destination_path)

    def copy_file(self, source_path: str, destination_path: str) -> Dict[str, Any]:
        return self._run("copy_file", lambda: self._copy_file(source_path, destination_path), source_path, destination_path)

    def list_directory(
        self,
        directory_path: str = ".",
        recursive: bool = False,
        show_hidden: bool = False,
        extension_filter: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        return self._run(
            "list_directory",
            lambda: self._list_directory(directory_path, recursive, show_hidden, extension_filter),
            directory_path,
        )

    def create_folder(self, folder_path: str, exist_ok: bool = True) -> Dict[str, Any]:
        return self._run("create_folder", lambda: self._create_folder(folder_path, exist_ok), folder_path)

    def delete_folder(self, folder_path: str, recursive: bool = False, confirm: bool = False) -> Dict[str, Any]:
        return self._run(
            "delete_folder",
            lambda: self._delete_folder(folder_path, recursive, confirm),
            folder_path,
        )

    def search_files(
        self,
        pattern: str,
        search_path: str = ".",
        recursive: bool = True,
        extension_filter: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        return self._run(
            "search_files",
            lambda: self._search_files(pattern, search_path, recursive, extension_filter),
            search_path,
        )

    def get_file_metadata(self, path: str) -> Dict[str, Any]:
        return self._run("get_file_metadata", lambda: self._get_metadata(path), path)

    def get_file_size(self, file_path: str) -> Dict[str, Any]:
        return self._run("get_file_size", lambda: self._get_size(file_path), file_path)

    def file_exists(self, path: str) -> Dict[str, Any]:
        return self._run("file_exists", lambda: self._file_exists(path), path)

    def is_file(self, path: str) -> Dict[str, Any]:
        return self._run("is_file", lambda: self._is_file(path), path)

    def is_dir(self, path: str) -> Dict[str, Any]:
        return self._run("is_dir", lambda: self._is_dir(path), path)

    def get_operation_history(self, limit: int = 100) -> Dict[str, Any]:
        records = self.history.list(limit=limit)
        return {"success": True, "count": len(records), "history": records}

    def analyze_file_importance(self, file_path: str) -> Dict[str, Any]:
        metadata = self.get_file_metadata(file_path)
        if not metadata.get("success"):
            return metadata

        meta = metadata["metadata"]
        modified_iso = meta.get("modified")
        days_old = 365
        if modified_iso:
            modified_dt = datetime.fromisoformat(modified_iso)
            days_old = max(0, (datetime.now() - modified_dt).days)

        recency_score = max(0.0, 1.0 - (days_old / 365.0))
        size = int(meta.get("size", 0))
        size_score = 0.1 if size == 0 else 0.8 if size > 100 * 1024 * 1024 else 0.5

        history = self.history.list(limit=500)
        access_count = 0
        for item in history:
            if item.get("path") == meta.get("path") and item.get("success"):
                access_count += 1
        frequency_score = min(1.0, access_count / 10.0)

        extension = (meta.get("extension") or "").lower()
        critical = extension in {".py", ".js", ".json", ".yml", ".yaml", ".ini", ".toml"}

        score = min(1.0, recency_score * 0.3 + frequency_score * 0.4 + size_score * 0.2 + (0.1 if critical else 0.0))
        level = "high" if score > 0.7 else "medium" if score > 0.4 else "low"

        return {
            "success": True,
            "file_path": meta.get("path"),
            "importance_score": score,
            "importance_level": level,
            "breakdown": {
                "recency": recency_score,
                "frequency": frequency_score,
                "size": size_score,
                "critical_extension": critical,
            },
            "message": f"File importance: {level} ({score:.2f})",
        }

    def _create_file(self, file_path: str, content: str, overwrite: bool) -> Dict[str, Any]:
        target = self.guard.resolve_path(file_path)
        if target.exists() and not overwrite:
            raise FileExistsError(f"File already exists: {file_path}")
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")
        return {"path": str(target), "size": target.stat().st_size, "message": f"Created file: {target.name}"}

    def _read_file(self, file_path: str, encoding: str) -> Dict[str, Any]:
        target = self.guard.resolve_path(file_path, must_exist=True)
        if not target.is_file():
            raise IsADirectoryError(f"Not a file: {file_path}")
        size = target.stat().st_size
        if size > self.config.max_read_bytes:
            raise ValueError(f"File too large ({size} bytes > {self.config.max_read_bytes} bytes)")
        content = target.read_text(encoding=encoding)
        return {"path": str(target), "content": content, "size": len(content), "message": f"Read file: {target.name}"}

    def _write_file(self, file_path: str, content: str, encoding: str, append: bool) -> Dict[str, Any]:
        target = self.guard.resolve_path(file_path)
        target.parent.mkdir(parents=True, exist_ok=True)
        mode = "a" if append else "w"
        with target.open(mode, encoding=encoding) as f:
            f.write(content)
        return {
            "path": str(target),
            "size": target.stat().st_size,
            "mode": mode,
            "message": f"{'Appended' if append else 'Wrote'} file: {target.name}",
        }

    def _delete_file(self, file_path: str, confirm: bool) -> Dict[str, Any]:
        target = self.guard.resolve_path(file_path, must_exist=True)
        if not target.is_file():
            raise IsADirectoryError(f"Not a file: {file_path}")
        self._require_confirmation(confirm, "delete_file")
        target.unlink()
        return {"path": str(target), "message": f"Deleted file: {target.name}"}

    def _rename_file(self, source_path: str, new_name: str) -> Dict[str, Any]:
        source = self.guard.resolve_path(source_path, must_exist=True)
        if not source.is_file():
            raise IsADirectoryError(f"Not a file: {source_path}")
        if "/" in new_name or "\\" in new_name:
            raise ValueError("new_name must be a file name, not a path")
        destination = source.with_name(new_name)
        self.guard._ensure_inside_workspace(destination)
        source.rename(destination)
        return {"source": str(source), "destination": str(destination), "message": f"Renamed to {new_name}"}

    def _move_file(self, source_path: str, destination_path: str) -> Dict[str, Any]:
        source = self.guard.resolve_path(source_path, must_exist=True)
        destination = self.guard.resolve_path(destination_path)
        destination.parent.mkdir(parents=True, exist_ok=True)
        moved = shutil.move(str(source), str(destination))
        return {"source": str(source), "destination": str(moved), "message": "Moved successfully"}

    def _copy_file(self, source_path: str, destination_path: str) -> Dict[str, Any]:
        source = self.guard.resolve_path(source_path, must_exist=True)
        destination = self.guard.resolve_path(destination_path)
        destination.parent.mkdir(parents=True, exist_ok=True)
        if source.is_dir():
            shutil.copytree(source, destination, dirs_exist_ok=True)
        else:
            shutil.copy2(source, destination)
        return {"source": str(source), "destination": str(destination), "message": "Copied successfully"}

    def _list_directory(
        self,
        directory_path: str,
        recursive: bool,
        show_hidden: bool,
        extension_filter: Optional[List[str]],
    ) -> Dict[str, Any]:
        directory = self.guard.resolve_path(directory_path, must_exist=True)
        if not directory.is_dir():
            raise NotADirectoryError(f"Not a directory: {directory_path}")

        normalized_exts = self._normalize_extension_filter(extension_filter)
        items: List[Dict[str, Any]] = []
        iterator = directory.rglob("*") if recursive else directory.iterdir()
        for item in iterator:
            if not show_hidden and item.name.startswith("."):
                continue
            if normalized_exts and item.is_file() and item.suffix.lower() not in normalized_exts:
                continue
            stat = item.stat()
            items.append(
                {
                    "name": item.name,
                    "path": str(item),
                    "is_file": item.is_file(),
                    "is_dir": item.is_dir(),
                    "size": stat.st_size if item.is_file() else 0,
                    "modified": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                    "extension": item.suffix.lower(),
                }
            )

        return {"path": str(directory), "count": len(items), "items": items, "message": f"Listed {len(items)} items"}

    def _create_folder(self, folder_path: str, exist_ok: bool) -> Dict[str, Any]:
        target = self.guard.resolve_path(folder_path)
        target.mkdir(parents=True, exist_ok=exist_ok)
        return {"path": str(target), "message": f"Created folder: {target.name}"}

    def _delete_folder(self, folder_path: str, recursive: bool, confirm: bool) -> Dict[str, Any]:
        target = self.guard.resolve_path(folder_path, must_exist=True)
        if not target.is_dir():
            raise NotADirectoryError(f"Not a folder: {folder_path}")
        self._require_confirmation(confirm, "delete_folder")
        if recursive:
            shutil.rmtree(target)
        else:
            target.rmdir()
        return {"path": str(target), "message": f"Deleted folder: {target.name}"}

    def _search_files(
        self,
        pattern: str,
        search_path: str,
        recursive: bool,
        extension_filter: Optional[List[str]],
    ) -> Dict[str, Any]:
        directory = self.guard.resolve_path(search_path, must_exist=True)
        if not directory.is_dir():
            raise NotADirectoryError(f"Not a directory: {search_path}")

        normalized_exts = self._normalize_extension_filter(extension_filter)
        candidates = directory.rglob("*") if recursive else directory.iterdir()
        matches: List[Dict[str, Any]] = []
        pattern_lower = pattern.lower()
        for item in candidates:
            if not item.is_file():
                continue
            if pattern_lower not in item.name.lower():
                continue
            if normalized_exts and item.suffix.lower() not in normalized_exts:
                continue
            matches.append(
                {
                    "name": item.name,
                    "path": str(item),
                    "size": item.stat().st_size,
                    "extension": item.suffix.lower(),
                }
            )
        return {"path": str(directory), "pattern": pattern, "count": len(matches), "matches": matches}

    def _get_metadata(self, path: str) -> Dict[str, Any]:
        target = self.guard.resolve_path(path)
        exists = target.exists()
        stat = target.stat() if exists else None
        mime_type = None
        if target.suffix:
            mime_type = mimetypes.guess_type(str(target))[0]
        metadata = FileMetadata(
            path=str(target),
            name=target.name,
            exists=exists,
            is_file=target.is_file() if exists else False,
            is_dir=target.is_dir() if exists else False,
            size=stat.st_size if (exists and target.is_file()) else 0,
            size_human=self._bytes_to_human(stat.st_size) if (exists and target.is_file()) else "0.00 B",
            extension=target.suffix.lower(),
            mime_type=mime_type,
            created=datetime.fromtimestamp(stat.st_ctime).isoformat() if exists else None,
            modified=datetime.fromtimestamp(stat.st_mtime).isoformat() if exists else None,
            accessed=datetime.fromtimestamp(stat.st_atime).isoformat() if exists else None,
        )
        return {"metadata": metadata.to_dict(), "message": f"Metadata for {target.name}"}

    def _get_size(self, file_path: str) -> Dict[str, Any]:
        target = self.guard.resolve_path(file_path, must_exist=True)
        if not target.is_file():
            raise IsADirectoryError(f"Not a file: {file_path}")
        size = target.stat().st_size
        return {"path": str(target), "size": size, "size_human": self._bytes_to_human(size)}

    def _file_exists(self, path: str) -> Dict[str, Any]:
        target = self.guard.resolve_path(path)
        return {"path": str(target), "exists": target.exists()}

    def _is_file(self, path: str) -> Dict[str, Any]:
        target = self.guard.resolve_path(path)
        return {"path": str(target), "is_file": target.is_file()}

    def _is_dir(self, path: str) -> Dict[str, Any]:
        target = self.guard.resolve_path(path)
        return {"path": str(target), "is_dir": target.is_dir()}

    def _run(self, operation: str, fn, path: Optional[str] = None, target: Optional[str] = None) -> Dict[str, Any]:
        try:
            payload = fn() or {}
            response = {"success": True, **payload}
            self._record(operation, True, response.get("message", "ok"), path, target, payload)
            return response
        except (WorkspaceSecurityError, FileNotFoundError, FileExistsError, ValueError, OSError) as exc:
            msg = str(exc)
            self._record(operation, False, msg, path, target, {"error_type": exc.__class__.__name__})
            return {"success": False, "error": msg}
        except Exception as exc:
            msg = f"Unexpected error: {exc}"
            self._record(operation, False, msg, path, target, {"error_type": exc.__class__.__name__})
            return {"success": False, "error": msg}

    def _record(
        self,
        operation: str,
        success: bool,
        message: str,
        path: Optional[str],
        target: Optional[str],
        details: Dict[str, Any],
    ) -> None:
        self._ensure_logger()
        self.logger.info(
            "operation=%s success=%s path=%s target=%s message=%s",
            operation,
            success,
            path,
            target,
            message,
        )
        self.history.append(OperationRecord.new(operation, success, message, path=path, target=target, details=details))

    def _require_confirmation(self, confirm: bool, operation: str) -> None:
        if self.config.require_delete_confirmation and not confirm:
            raise PermissionError(f"{operation} requires confirmation (set confirm=True).")

    @staticmethod
    def _bytes_to_human(size: int) -> str:
        value = float(size)
        for unit in ("B", "KB", "MB", "GB", "TB"):
            if value < 1024:
                return f"{value:.2f} {unit}"
            value /= 1024
        return f"{value:.2f} PB"

    @staticmethod
    def _normalize_extension_filter(extension_filter: Optional[List[str]]) -> Optional[set]:
        if not extension_filter:
            return None
        normalized = set()
        for ext in extension_filter:
            if not ext:
                continue
            value = ext.lower().strip()
            if not value.startswith("."):
                value = "." + value
            normalized.add(value)
        return normalized or None

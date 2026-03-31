from dataclasses import dataclass, asdict
from datetime import datetime
from typing import Any, Dict, List, Optional


@dataclass
class FileMetadata:
    path: str
    name: str
    exists: bool
    is_file: bool
    is_dir: bool
    size: int
    size_human: str
    extension: str
    mime_type: Optional[str]
    created: Optional[str]
    modified: Optional[str]
    accessed: Optional[str]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class OperationRecord:
    timestamp: str
    operation: str
    path: Optional[str]
    target: Optional[str]
    success: bool
    message: str
    details: Dict[str, Any]

    @staticmethod
    def new(
        operation: str,
        success: bool,
        message: str,
        path: Optional[str] = None,
        target: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
    ) -> "OperationRecord":
        return OperationRecord(
            timestamp=datetime.utcnow().isoformat() + "Z",
            operation=operation,
            path=path,
            target=target,
            success=success,
            message=message,
            details=details or {},
        )

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class ToolRequest:
    name: str
    args: Dict[str, Any]


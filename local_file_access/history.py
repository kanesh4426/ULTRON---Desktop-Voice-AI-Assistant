import json
from pathlib import Path
from typing import Any, Dict, List

from .models import OperationRecord


class OperationHistory:
    def __init__(self, history_file: Path, max_records: int = 1000):
        self.history_file = history_file
        self.max_records = max_records
        self.history_file.parent.mkdir(parents=True, exist_ok=True)
        if not self.history_file.exists():
            self.history_file.write_text("", encoding="utf-8")

    def append(self, record: OperationRecord) -> None:
        with self.history_file.open("a", encoding="utf-8") as f:
            f.write(json.dumps(record.to_dict(), ensure_ascii=False) + "\n")

        self._trim()

    def list(self, limit: int = 100) -> List[Dict[str, Any]]:
        if limit <= 0:
            return []
        lines = self.history_file.read_text(encoding="utf-8").splitlines()
        selected = lines[-limit:]
        output: List[Dict[str, Any]] = []
        for line in selected:
            try:
                output.append(json.loads(line))
            except json.JSONDecodeError:
                continue
        return output

    def _trim(self) -> None:
        lines = self.history_file.read_text(encoding="utf-8").splitlines()
        if len(lines) <= self.max_records:
            return
        keep = lines[-self.max_records :]
        self.history_file.write_text("\n".join(keep) + "\n", encoding="utf-8")


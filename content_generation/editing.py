from __future__ import annotations

import re
from typing import Iterable

from .models import DeltaUpdate


class DeltaEditor:
    def apply(self, content: str, delta: DeltaUpdate | Iterable[DeltaUpdate]) -> str:
        updates = [delta] if isinstance(delta, DeltaUpdate) else list(delta)
        updated = content
        for item in updates:
            updated = self._apply_single(updated, item)
        return updated

    def _apply_single(self, content: str, update: DeltaUpdate) -> str:
        operation = (update.operation or "").strip().lower()
        if operation == "replace":
            return self._replace_nth(
                content,
                target=update.target,
                replacement=update.content,
                occurrence=update.occurrence,
            )
        if operation == "insert_after":
            return self._insert_relative(
                content,
                target=update.target,
                addition=update.content,
                occurrence=update.occurrence,
                before=False,
            )
        if operation == "insert_before":
            return self._insert_relative(
                content,
                target=update.target,
                addition=update.content,
                occurrence=update.occurrence,
                before=True,
            )
        if operation == "append":
            separator = ""
            if content and not content.endswith("\n"):
                separator = "\n\n"
            return f"{content}{separator}{update.content}".strip()
        if operation == "section_replace":
            return self._replace_section(content, update.target, update.content)
        raise ValueError(f"Unsupported delta operation: {update.operation}")

    @staticmethod
    def _replace_nth(content: str, target: str, replacement: str, occurrence: int) -> str:
        start = DeltaEditor._locate(content, target, occurrence)
        end = start + len(target)
        return f"{content[:start]}{replacement}{content[end:]}"

    @staticmethod
    def _insert_relative(
        content: str,
        target: str,
        addition: str,
        occurrence: int,
        before: bool,
    ) -> str:
        start = DeltaEditor._locate(content, target, occurrence)
        index = start if before else start + len(target)
        return f"{content[:index]}{addition}{content[index:]}"

    @staticmethod
    def _replace_section(content: str, target: str, replacement: str) -> str:
        heading = target.lstrip("#").strip()
        pattern = re.compile(
            rf"(?ms)(^##+\s+{re.escape(heading)}\s*$)(.*?)(?=^##+\s+|\Z)"
        )
        match = pattern.search(content)
        if not match:
            raise ValueError(f"Heading not found for delta update: {target}")
        updated = f"{match.group(1)}\n{replacement.strip()}\n\n"
        return f"{content[:match.start()]}{updated}{content[match.end():]}".rstrip()

    @staticmethod
    def _locate(content: str, target: str, occurrence: int) -> int:
        if occurrence < 1:
            raise ValueError("occurrence must be >= 1")
        offset = 0
        start = -1
        for _ in range(occurrence):
            start = content.find(target, offset)
            if start == -1:
                raise ValueError(f"Delta target not found: {target}")
            offset = start + len(target)
        return start

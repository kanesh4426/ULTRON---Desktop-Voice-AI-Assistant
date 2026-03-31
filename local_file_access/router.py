import re
from typing import Any, Dict, Optional

from .tools import FileToolExecutor


class AIFileCommandRouter:
    """
    Lightweight natural-language command router for file tools.
    """

    def __init__(self, executor: FileToolExecutor):
        self.executor = executor

    def route(self, command_text: str) -> Dict[str, Any]:
        text = (command_text or "").strip()
        if not text:
            return {"success": False, "error": "Empty command"}

        m = re.search(r"(?:create|new)\s+file\s+(.+)$", text, re.IGNORECASE)
        if m:
            path = m.group(1).strip()
            return self.executor.execute("create_file", file_path=path, content="")

        m = re.search(r"(?:read|open)\s+file\s+(.+)$", text, re.IGNORECASE)
        if m:
            return self.executor.execute("read_file", file_path=m.group(1).strip())

        m = re.search(r"append\s+(.+?)\s+to\s+file\s+(.+)$", text, re.IGNORECASE)
        if m:
            return self.executor.execute("append_file", file_path=m.group(2).strip(), content=m.group(1))

        m = re.search(r"write\s+(.+?)\s+to\s+file\s+(.+)$", text, re.IGNORECASE)
        if m:
            return self.executor.execute("write_file", file_path=m.group(2).strip(), content=m.group(1))

        m = re.search(r"delete\s+file\s+(.+)$", text, re.IGNORECASE)
        if m:
            return self.executor.execute("delete_file", file_path=m.group(1).strip(), confirm=True)

        m = re.search(r"rename\s+file\s+(.+?)\s+to\s+(.+)$", text, re.IGNORECASE)
        if m:
            return self.executor.execute("rename_file", source_path=m.group(1).strip(), new_name=m.group(2).strip())

        m = re.search(r"move\s+(.+?)\s+to\s+(.+)$", text, re.IGNORECASE)
        if m:
            return self.executor.execute("move_file", source_path=m.group(1).strip(), destination_path=m.group(2).strip())

        m = re.search(r"copy\s+(.+?)\s+to\s+(.+)$", text, re.IGNORECASE)
        if m:
            return self.executor.execute("copy_file", source_path=m.group(1).strip(), destination_path=m.group(2).strip())

        m = re.search(r"(?:list|show)\s+(?:directory|folder)\s*(.*)$", text, re.IGNORECASE)
        if m:
            path = m.group(1).strip() or "."
            return self.executor.execute("list_directory", directory_path=path)

        m = re.search(r"(?:create|new)\s+(?:folder|directory)\s+(.+)$", text, re.IGNORECASE)
        if m:
            return self.executor.execute("create_folder", folder_path=m.group(1).strip())

        m = re.search(r"delete\s+(?:folder|directory)\s+(.+)$", text, re.IGNORECASE)
        if m:
            return self.executor.execute("delete_folder", folder_path=m.group(1).strip(), recursive=True, confirm=True)

        m = re.search(r"search\s+files?\s+(.+?)(?:\s+in\s+(.+))?$", text, re.IGNORECASE)
        if m:
            pattern = m.group(1).strip()
            path = (m.group(2) or ".").strip()
            return self.executor.execute("search_files", pattern=pattern, search_path=path, recursive=True)

        m = re.search(r"(?:metadata|info)\s+(.+)$", text, re.IGNORECASE)
        if m:
            return self.executor.execute("get_file_metadata", path=m.group(1).strip())

        return {"success": False, "error": f"Could not route command: {command_text}"}

from typing import Any, Dict

from local_file_access import FileManager, FileManagerConfig


class FileTool:
    name = "file_tool"

    def __init__(self, workspace_root: str):
        cfg = FileManagerConfig(workspace_root=workspace_root, require_delete_confirmation=True)
        self.manager = FileManager(cfg)

    def read_local_file(self, path: str) -> Dict[str, Any]:
        return self.manager.read_file(path)

    def list_directory(self, path: str = ".") -> Dict[str, Any]:
        return self.manager.list_directory(directory_path=path)

    def execute(self, action: str, **kwargs: Any) -> Dict[str, Any]:
        if action == "read_local_file":
            return self.read_local_file(kwargs["path"])
        if action == "list_directory":
            return self.list_directory(kwargs.get("path", "."))
        if action == "write_file":
            return self.manager.write_file(file_path=kwargs["path"], content=kwargs.get("content", ""))
        if action == "search_files":
            return self.manager.search_files(
                pattern=kwargs["pattern"],
                search_path=kwargs.get("path", "."),
                recursive=True,
            )
        return {"success": False, "error": f"Unsupported file action: {action}"}

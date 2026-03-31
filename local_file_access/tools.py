from typing import Any, Callable, Dict

from .manager import FileManager


class FileToolExecutor:
    """
    Tool-based adapter for AI/tool invocations.
    """

    def __init__(self, manager: FileManager):
        self.manager = manager
        self._tools: Dict[str, Callable[..., Dict[str, Any]]] = {
            "create_file": self.manager.create_file,
            "read_file": self.manager.read_file,
            "write_file": self.manager.write_file,
            "append_file": self.manager.append_file,
            "delete_file": self.manager.delete_file,
            "rename_file": self.manager.rename_file,
            "move_file": self.manager.move_file,
            "copy_file": self.manager.copy_file,
            "list_directory": self.manager.list_directory,
            "create_folder": self.manager.create_folder,
            "delete_folder": self.manager.delete_folder,
            "search_files": self.manager.search_files,
            "get_file_metadata": self.manager.get_file_metadata,
            "get_file_size": self.manager.get_file_size,
            "get_operation_history": self.manager.get_operation_history,
            "analyze_file_importance": self.manager.analyze_file_importance,
        }

    def execute(self, tool_name: str, **kwargs: Any) -> Dict[str, Any]:
        fn = self._tools.get(tool_name)
        if not fn:
            return {"success": False, "error": f"Unknown tool: {tool_name}"}
        return fn(**kwargs)

    def available_tools(self) -> Dict[str, str]:
        return {
            name: fn.__name__
            for name, fn in self._tools.items()
        }


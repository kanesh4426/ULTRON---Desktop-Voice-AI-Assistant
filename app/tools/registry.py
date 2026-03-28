from typing import Any, Dict

from app.tools.executions.app_access_tool import AppAccessTool
from app.tools.executions.code_execution_tool import CodeExecutionTool
from app.tools.executions.file_tool import FileTool
from app.tools.executions.web_search_tool import WebSearchTool


class SystemToolRegistry:
    def __init__(self, workspace_root: str):
        self.file_tool = FileTool(workspace_root=workspace_root)
        self.web_tool = WebSearchTool()
        self.code_tool = CodeExecutionTool()
        self.app_access_tool = AppAccessTool()

    def execute(self, tool_name: str, action: str, **kwargs: Any) -> Dict[str, Any]:
        if tool_name == "file_tool":
            return self.file_tool.execute(action, **kwargs)
        if tool_name == "web_search_tool":
            return self.web_tool.execute(action, **kwargs)
        if tool_name == "code_execution_tool":
            return self.code_tool.execute(action, **kwargs)
        if tool_name == "app_access_tool":
            return self.app_access_tool.execute(action, **kwargs)
        return {"success": False, "error": f"Unknown tool: {tool_name}"}

    def available_tools(self):
        return {
            "file_tool": ["read_local_file", "list_directory", "write_file", "search_files"],
            "app_access_tool": ["open_application", "close_application", "open_website", "is_application_running", "list_running_applications", "list_installed_apps", "get_app_info", "process_command"],
            "web_search_tool": ["web_search"],
            "code_execution_tool": ["execute_python_code"],
        }

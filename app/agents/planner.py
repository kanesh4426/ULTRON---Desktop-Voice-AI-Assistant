from typing import Optional

from app.models.tool_call import ToolCall


class AgentPlanner:
    """
    Lightweight planner to decide if a tool call is needed.
    """

    def plan(self, user_text: str) -> Optional[ToolCall]:
        t = user_text.lower().strip()

        if t.startswith("read file "):
            return ToolCall("file_tool", {"action": "read_local_file", "path": user_text[10:].strip()})
        if t.startswith("list dir"):
            path = user_text.replace("list dir", "", 1).strip() or "."
            return ToolCall("file_tool", {"action": "list_directory", "path": path})
        if t.startswith("search web "):
            return ToolCall("web_search_tool", {"action": "web_search", "query": user_text[11:].strip()})
        if t.startswith("run python "):
            return ToolCall("code_execution_tool", {"action": "execute_python_code", "code": user_text[11:]})
        if t.startswith(("open ", "close ", "start ", "launch ", "run ")):
            return ToolCall("app_access_tool", {"action": "process_command", "command": user_text})

        return None

from typing import Any, Dict

from app_access import AppManager, AppManagerConfig


class AppAccessTool:
    name = "app_access_tool"

    def __init__(self) -> None:
        self.manager = AppManager(AppManagerConfig())

    def execute(self, action: str, **kwargs: Any) -> Dict[str, Any]:
        if action == "open_application":
            return self.manager.open_application(kwargs["app_name"])
        if action == "close_application":
            return self.manager.close_application(kwargs["app_name"])
        if action == "open_website":
            return self.manager.open_website(kwargs["target"])
        if action == "is_application_running":
            return self.manager.is_application_running(kwargs["app_name"])
        if action == "list_running_applications":
            return self.manager.list_running_applications(kwargs.get("limit", 200))
        if action == "list_installed_apps":
            return self.manager.list_installed_apps()
        if action == "get_app_info":
            return self.manager.get_app_info(kwargs["app_name"])
        if action == "process_command":
            return self.manager.process_command(kwargs["command"])
        return {"success": False, "error": f"Unsupported app access action: {action}"}

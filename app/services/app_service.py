from typing import Any, Dict, List, Optional
from app_access.manager import AppManager

class AppController:
    """
    Thin wrapper over AppManager for backward compatibility.
    """

    def __init__(self) -> None:
        self.manager = AppManager()
        self.current_os = self.manager.current_os

    def refresh_app_index(self) -> None:
        self.manager.refresh_app_index()

    def is_app_installed_locally(self, app_name: str) -> Dict[str, Any]:
        return self.manager.is_app_installed_locally(app_name)

    def has_web_version(self, app_name: str) -> Dict[str, Any]:
        return self.manager.has_web_version(app_name)

    def open_application_smart(self, app_name: str) -> Dict[str, Any]:
        return self.manager.open_application(app_name)

    def close_application(self, app_name: str) -> Dict[str, Any]:
        return self.manager.close_application(app_name)

    def is_app_running(self, app_name: str) -> Dict[str, Any]:
        return self.manager.is_application_running(app_name)

    def process_command(self, command: str) -> Dict[str, Any]:
        return self.manager.process_command(command)

    def get_app_info(self, app_name: str) -> Dict[str, Any]:
        return self.manager.get_app_info(app_name)


def open_app(app_name: str) -> Dict[str, Any]:
    return AppManager().open_application(app_name)


def close_app(app_name: str) -> Dict[str, Any]:
    return AppManager().close_application(app_name)


def process_command(command: str) -> Dict[str, Any]:
    return AppManager().process_command(command)


def is_app_installed(app_name: str) -> Dict[str, Any]:
    return AppManager().is_app_installed_locally(app_name)


def get_app_info(app_name: str) -> Dict[str, Any]:
    return AppManager().get_app_info(app_name)

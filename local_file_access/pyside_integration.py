from typing import Any, Dict

from PySide6.QtCore import QObject, Signal, Slot

from .router import AIFileCommandRouter


class FileAccessBridge(QObject):
    """
    Example bridge to connect FileManager tools to a PySide6 UI.
    """

    operationCompleted = Signal(dict)

    def __init__(self, router: AIFileCommandRouter):
        super().__init__()
        self.router = router

    @Slot(str)
    def execute_text_command(self, command_text: str) -> None:
        result = self.router.route(command_text)
        self.operationCompleted.emit(result)

    @Slot(str, "QVariantMap")
    def execute_tool(self, tool_name: str, payload: Dict[str, Any]) -> None:
        result = self.router.executor.execute(tool_name, **(payload or {}))
        self.operationCompleted.emit(result)


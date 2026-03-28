from typing import Dict

from app.models.tool_call import ToolCall
from app.tools.registry import SystemToolRegistry


class ToolExecutor:
    def __init__(self, registry: SystemToolRegistry):
        self.registry = registry

    def execute(self, call: ToolCall) -> Dict:
        args = dict(call.arguments)
        action = args.pop("action", "")
        return self.registry.execute(call.tool_name, action=action, **args)

from dataclasses import dataclass, field
from typing import Any, Dict


@dataclass
class ToolCall:
    tool_name: str
    arguments: Dict[str, Any] = field(default_factory=dict)


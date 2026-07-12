"""Computer-use tool wrapper.

Delegates to the hardened computer_use service.
"""

from __future__ import annotations

from app.services.computer_use import run_tool
from app.services.tools.base import Tool


class ComputerUseTool(Tool):
    """Tool for taking desktop actions or running local commands."""

    name = "computer_use"
    description = (
        "Take actions on the local machine: screenshot, click, type, keypress, scroll. "
        "For shell commands, use the dedicated 'shell' tool instead. "
        "Will fail if disarmed by the user."
    )
    requires_approval = True
    schema = {
        "type": "object",
        "properties": {
            "action": {
                "type": "string",
                "enum": ["screenshot", "click", "type", "keypress", "scroll"],
                "description": "The desktop action to perform.",
            },
            "x": {"type": "integer", "description": "X coordinate for click."},
            "y": {"type": "integer", "description": "Y coordinate for click."},
            "text": {"type": "string", "description": "Text to type."},
            "key": {"type": "string", "description": "Key to press."},
            "clicks": {"type": "integer", "description": "Scroll clicks (default 3)."},
            "direction": {"type": "string", "description": "Scroll direction: up or down (default down)."},
        },
        "required": ["action"],
    }

    def run(self, **kwargs) -> str:
        action = kwargs.pop("action")
        try:
            return run_tool(action, kwargs)
        except Exception as exc:
            return f"Error: {exc}"

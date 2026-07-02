"""Computer-use tool wrapper."""

from __future__ import annotations

from app.services.computer_use import run_tool
from app.services.tools.base import Tool


class ComputerUseTool(Tool):
    """Tool for taking desktop actions or running local commands."""

    name = "computer_use"
    description = (
        "Take actions on the local machine: screenshot, click, type, keypress, shell. "
        "Will fail if disarmed by the user."
    )
    requires_approval = True
    schema = {
        "type": "object",
        "properties": {
            "action": {
                "type": "string",
                "enum": ["screenshot", "click", "type", "keypress", "shell"],
                "description": "The action to perform.",
            },
            "x": {"type": "integer", "description": "X coordinate for click."},
            "y": {"type": "integer", "description": "Y coordinate for click."},
            "text": {"type": "string", "description": "Text to type."},
            "key": {"type": "string", "description": "Key to press."},
            "command": {"type": "string", "description": "Shell command to run (if shell)."},
        },
        "required": ["action"],
    }

    def run(self, **kwargs) -> str:
        action = kwargs.pop("action")
        try:
            return run_tool(action, kwargs)
        except Exception as exc:
            return f"Error: {exc}"

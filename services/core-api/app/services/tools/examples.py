"""Trivial example tools and registration helper."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from app.services.tools.base import Tool
from app.services.tools.registry import ToolRegistry, registry
from app.services.tools.computer import ComputerUseTool
from app.services.tools.tasks import TaskTool


class EchoTool(Tool):
    name = "echo"
    description = "Echo back the provided text."

    @property
    def schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {"text": {"type": "string"}},
            "required": ["text"],
        }

    def run(self, **kwargs: Any) -> Any:
        return {"text": kwargs.get("text", "")}


class TimeTool(Tool):
    name = "time"
    description = "Return the current UTC time in ISO 8601 format."

    def run(self, **kwargs: Any) -> Any:
        return {"utc": datetime.now(timezone.utc).isoformat()}


def register_example_tools(target: ToolRegistry | None = None) -> None:
    """Register built-in example tools into the given (or default) registry."""
    target = target or registry
    for tool in (EchoTool(), TimeTool(), ComputerUseTool(), TaskTool()):
        if target.get(tool.name) is None:
            target.register(tool)

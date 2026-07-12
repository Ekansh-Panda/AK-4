"""Register all built-in tools into the default registry."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from app.services.tools.base import Tool
from app.services.tools.registry import registry
from app.services.tools.computer import ComputerUseTool
from app.services.tools.tasks import TaskTool
from app.services.tools.shell import ShellTool
from app.services.tools.files import (
    FsWriteTool,
    FsReadTool,
    FsListTool,
    FsDeleteTool,
)
from app.services.tools.browser import BrowserTool
from app.services.tools.system import (
    InstallTool,
    ProcessTool,
    ServiceTool,
    ClipboardTool,
    NotifyTool,
    GitTool,
    DockerTool,
)


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
    for tool in (
        EchoTool(),
        TimeTool(),
        ComputerUseTool(),
        ShellTool(),
        FsWriteTool(),
        FsReadTool(),
        FsListTool(),
        FsDeleteTool(),
        BrowserTool(),
        TaskTool(),
        InstallTool(),
        ProcessTool(),
        ServiceTool(),
        ClipboardTool(),
        NotifyTool(),
        GitTool(),
        DockerTool(),
    ):
        if target.get(tool.name) is None:
            target.register(tool)

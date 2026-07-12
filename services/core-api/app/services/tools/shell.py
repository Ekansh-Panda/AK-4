"""Shell execution tool.

Executes commands as list-of-arguments (no shell=True) with full stdout/stderr capture.
"""

from __future__ import annotations

import subprocess
from typing import Any

from app.core.logging import get_logger
from app.services.tools.base import Tool

logger = get_logger(__name__)


class ShellTool(Tool):
    """Execute shell commands as a list of arguments without shell=True."""

    name = "shell"
    description = (
        "Execute a shell command. Accepts a list of arguments (command + args). "
        "Returns stdout, stderr, return code, and elapsed time. "
        "Requires approval and COMPUTER_USE_ENABLED + COMPUTER_USE_SHELL_ENABLED."
    )
    requires_approval = True

    @property
    def schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "command": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Command and arguments as a list of strings, e.g. ['ls', '-la', '/']",
                    "minItems": 1,
                },
                "cwd": {
                    "type": "string",
                    "description": "Optional working directory. Defaults to current directory.",
                },
                "timeout": {
                    "type": "integer",
                    "description": "Timeout in seconds. Default 30.",
                },
            },
            "required": ["command"],
        }

    def run(self, **kwargs: Any) -> Any:
        command: list[str] = kwargs.get("command", [])
        cwd: str | None = kwargs.get("cwd")
        timeout: int = kwargs.get("timeout", 30)

        if not command or not isinstance(command, list):
            return {"error": "command must be a non-empty list of strings"}

        if not settings.COMPUTER_USE_ENABLED or not settings.COMPUTER_USE_SHELL_ENABLED:
            return {"error": "Shell execution is disabled in config."}

        try:
            result = subprocess.run(
                command,
                capture_output=True,
                text=True,
                timeout=timeout,
                cwd=cwd,
            )
            return {
                "command": command,
                "return_code": result.returncode,
                "stdout": result.stdout,
                "stderr": result.stderr,
                "elapsed_s": round(result.elapsed_time, 3) if hasattr(result, "elapsed_time") else None,
            }
        except subprocess.TimeoutExpired:
            return {"error": f"Command timed out after {timeout}s", "command": command}
        except FileNotFoundError:
            return {"error": f"Command not found: {command[0]}", "command": command}
        except Exception as exc:
            logger.error("Shell execution failed: %s", exc)
            return {"error": str(exc), "command": command}

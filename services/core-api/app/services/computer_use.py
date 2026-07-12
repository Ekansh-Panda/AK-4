"""Computer Use service — safety-sensitive desktop automation tools.

Implements arm/disarm toggle, audit logging, and restricted tool execution.
Off by default. Must be explicitly armed per session.
"""

from __future__ import annotations

import datetime
import json
import os
import subprocess
from datetime import datetime, timezone
from pathlib import Path

from pydantic import BaseModel

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)

# Single-process in-memory arm toggle for safety.
_armed = False

AUDIT_LOG_PATH = Path("data/computer_use_audit.log")


class AuditEntry(BaseModel):
    ts: str
    action: str
    args: dict
    outcome: str
    error: str | None = None


def is_armed() -> bool:
    return settings.COMPUTER_USE_ENABLED and _armed


def set_armed(state: bool) -> bool:
    global _armed
    if not settings.COMPUTER_USE_ENABLED:
        _armed = False
        return False
    _armed = state
    logger.warning("Computer use armed state changed to %s", _armed)
    return _armed


def log_audit_action(action: str, args: dict, outcome: str, error: str | None = None) -> None:
    """Append a safety audit log entry."""
    entry = AuditEntry(
        ts=datetime.now(timezone.utc).isoformat(),
        action=action,
        args=args,
        outcome=outcome,
        error=error,
    )
    AUDIT_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    with AUDIT_LOG_PATH.open("a", encoding="utf-8") as f:
        f.write(entry.model_dump_json() + "\n")


def get_audit_log(limit: int = 20) -> list[AuditEntry]:
    """Return the last N audit log entries."""
    if not AUDIT_LOG_PATH.exists():
        return []
    with AUDIT_LOG_PATH.open("r", encoding="utf-8") as f:
        lines = f.readlines()
    entries = []
    for line in lines[-limit:]:
        try:
            entries.append(AuditEntry.model_validate_json(line))
        except Exception:
            pass
    return entries


def execute_shell(command: list[str]) -> dict:
    """Execute a shell command as list-of-args without shell=True.

    Runs with cwd=None (current working directory) by default.
    Capture and return full stdout/stderr.
    """
    if not settings.COMPUTER_USE_SHELL_ENABLED:
        raise PermissionError("Shell execution is disabled in config.")

    if not command or not isinstance(command, list):
        raise ValueError("command must be a non-empty list of strings")

    try:
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=30,
            cwd=None,
        )
        return {
            "command": command,
            "return_code": result.returncode,
            "stdout": result.stdout,
            "stderr": result.stderr,
            "elapsed_s": None,
        }
    except subprocess.TimeoutExpired:
        return {"error": f"Command timed out after 30s", "command": command}
    except FileNotFoundError:
        return {"error": f"Command not found: {command[0]}", "command": command}
    except Exception as exc:
        raise RuntimeError(f"Shell failed: {exc}")


def execute_desktop_action(action: str, args: dict) -> str:
    """Execute screenshot, click, type, keypress using pyautogui.

    pyautogui is a HARD dependency when COMPUTER_USE_ENABLED=true.
    Raises ImportError immediately if pyautogui is not installed.
    """
    import pyautogui  # noqa: F401 — hard dependency, raised on ImportError

    try:
        if action == "screenshot":
            timestamp = int(datetime.now(timezone.utc).timestamp())
            path = Path(f"data/screenshot_{timestamp}.png")
            path.parent.mkdir(parents=True, exist_ok=True)
            pyautogui.screenshot(str(path))
            return f"Screenshot saved to {path}"
        elif action == "click":
            x = args.get("x")
            y = args.get("y")
            if x is not None and y is not None:
                pyautogui.click(x, y)
                return f"Clicked at ({x}, {y})"
            pyautogui.click()
            return "Clicked at current location"
        elif action == "type":
            text = args.get("text", "")
            pyautogui.write(text, interval=0.01)
            return f"Typed: {text}"
        elif action == "keypress":
            key = args.get("key", "")
            pyautogui.press(key)
            return f"Pressed key: {key}"
        elif action == "scroll":
            clicks = args.get("clicks", 3)
            direction = args.get("direction", "down")
            delta = clicks if direction == "down" else -clicks
            pyautogui.scroll(delta)
            return f"Scrolled {delta} clicks"
        else:
            raise ValueError(f"Unknown desktop action: {action}")
    except Exception as exc:
        raise RuntimeError(f"Desktop action failed: {exc}")


def run_tool(action: str, args: dict) -> str:
    """Main entrypoint for computer-use tool."""
    if not is_armed():
        log_audit_action(action, args, "Blocked", "Not armed")
        return "Error: Computer use is currently disarmed. Please arm it in settings."

    outcome = ""
    error = None
    try:
        if action == "shell":
            raw_cmd = args.get("command", "")
            if isinstance(raw_cmd, list):
                command = raw_cmd
            elif isinstance(raw_cmd, str) and raw_cmd.strip():
                raise ValueError("shell action requires command as a list-of-strings, not a raw string. Use the shell tool instead.")
            else:
                raise ValueError("shell action requires a non-empty command list")
            result = execute_shell(command)
            outcome = json.dumps(result)
        else:
            outcome = execute_desktop_action(action, args)
    except Exception as exc:
        error = str(exc)
        outcome = "Failed"
        raise
    finally:
        log_audit_action(
            action,
            args,
            outcome[:200] + ("..." if len(outcome) > 200 else outcome),
            error,
        )

    return outcome

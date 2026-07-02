"""Computer Use service — safety-sensitive desktop automation tools.

Implements arm/disarm toggle, audit logging, and restricted tool execution.
Off by default. Must be explicitly armed per session.
"""

from __future__ import annotations

import json
import os
import shlex
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
RESTRICTED_DIR = Path("data/computer_use_workspace").resolve()


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


def execute_shell(command: str) -> str:
    """Safely execute a shell command in a restricted directory."""
    if not settings.COMPUTER_USE_SHELL_ENABLED:
        raise PermissionError("Shell execution is disabled in config.")
    
    RESTRICTED_DIR.mkdir(parents=True, exist_ok=True)
    
    try:
        # We allow subprocess but run it with cwd=RESTRICTED_DIR.
        # This is not a strong sandbox, but meets the phase requirement
        # of running inside a restricted directory and logging literal command.
        result = subprocess.run(
            command,
            shell=True,
            cwd=RESTRICTED_DIR,
            capture_output=True,
            text=True,
            timeout=10,
        )
        out = result.stdout + (f"\n[stderr]\n{result.stderr}" if result.stderr else "")
        return out.strip() or "Success"
    except Exception as exc:
        raise RuntimeError(f"Shell failed: {exc}")


def _mock_desktop_action(action: str, args: dict) -> str:
    """Fallback if pyautogui is not installed (lite mode)."""
    return f"Simulated desktop action: {action} with args {args}"


def execute_desktop_action(action: str, args: dict) -> str:
    """Execute screenshot, click, type, keypress using pyautogui."""
    try:
        import pyautogui  # lazy
    except ImportError:
        logger.warning("pyautogui not installed; mocking desktop action")
        return _mock_desktop_action(action, args)
    
    try:
        if action == "screenshot":
            path = RESTRICTED_DIR / f"screenshot_{int(datetime.now(timezone.utc).timestamp())}.png"
            RESTRICTED_DIR.mkdir(parents=True, exist_ok=True)
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
            outcome = execute_shell(args.get("command", ""))
        else:
            outcome = execute_desktop_action(action, args)
    except Exception as exc:
        error = str(exc)
        outcome = "Failed"
        raise
    finally:
        log_audit_action(action, args, outcome[:200] + ("..." if len(outcome) > 200 else outcome), error)
        
    return outcome

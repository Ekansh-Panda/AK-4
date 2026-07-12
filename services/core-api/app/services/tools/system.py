"""System-level tools: install, process, service, clipboard, notify, git, docker."""

from __future__ import annotations

import os
import platform
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

from app.core.config import settings
from app.core.logging import get_logger
from app.services.tools.base import Tool

logger = get_logger(__name__)


def _detect_package_manager() -> str:
    system = platform.system().lower()
    if system == "windows":
        if shutil.which("winget"):
            return "winget"
        if shutil.which("choco"):
            return "choco"
        return "unknown"
    elif system == "darwin":
        if shutil.which("brew"):
            return "brew"
        return "unknown"
    elif system == "linux":
        if shutil.which("apt"):
            return "apt"
        if shutil.which("dnf"):
            return "dnf"
        if shutil.which("pacman"):
            return "pacman"
        return "unknown"
    return "unknown"


def _install_cmd(package: str, manager: str) -> list[str]:
    m = manager.lower()
    if m == "winget":
        return ["winget", "install", "--id", package, "--accept-package-agreements", "--accept-source-agreements"]
    elif m == "apt":
        return ["sudo", "apt-get", "install", "-y", package]
    elif m == "brew":
        return ["brew", "install", package]
    elif m == "choco":
        return ["choco", "install", "-y", package]
    elif m == "dnf":
        return ["sudo", "dnf", "install", "-y", package]
    elif m == "pacman":
        return ["sudo", "pacman", "-S", "--noconfirm", package]
    else:
        return [sys.executable, "-m", "pip", "install", package]


class InstallTool(Tool):
    """Install a system package using the appropriate package manager."""

    name = "install"
    description = "Install a system package. Auto-detects the OS and package manager."
    requires_approval = True

    @property
    def schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "package": {"type": "string", "description": "Package name to install."},
                "manager": {
                    "type": "string",
                    "enum": ["auto", "winget", "apt", "brew", "choco"],
                    "description": "Package manager to use. 'auto' detects from OS.",
                },
            },
            "required": ["package"],
        }

    def run(self, **kwargs: Any) -> Any:
        package = kwargs.get("package", "")
        manager = kwargs.get("manager", "auto")

        if not package:
            return {"error": "package is required"}

        if manager == "auto":
            manager = _detect_package_manager()

        cmd = _install_cmd(package, manager)
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=120,
            )
            return {
                "package": package,
                "manager": manager,
                "command": cmd,
                "return_code": result.returncode,
                "stdout": result.stdout,
                "stderr": result.stderr,
            }
        except subprocess.TimeoutExpired:
            return {"error": f"Install timed out for {package}", "package": package}
        except Exception as exc:
            logger.error("install failed: %s", exc)
            return {"error": str(exc), "package": package}


class ProcessTool(Tool):
    """Manage system processes: list, start, kill."""

    name = "process"
    description = "List, start, or kill system processes."
    requires_approval = False

    @property
    def schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "enum": ["list", "start", "kill"],
                    "description": "Process action.",
                },
                "name": {"type": "string", "description": "Process name (for start/kill)."},
                "pid": {"type": "integer", "description": "Process ID (for kill)."},
            },
            "required": ["action"],
        }

    def run(self, **kwargs: Any) -> Any:
        action = kwargs.get("action", "list")
        name = kwargs.get("name")
        pid = kwargs.get("pid")

        if action == "list":
            try:
                result = subprocess.run(["ps", "aux"], capture_output=True, text=True, timeout=10)
                lines = result.stdout.strip().splitlines()
                processes = []
                for line in lines[1:]:
                    parts = line.split(None, 10)
                    if len(parts) >= 11:
                        processes.append({
                            "user": parts[0],
                            "pid": int(parts[1]),
                            "cpu": parts[2],
                            "mem": parts[3],
                            "command": parts[10],
                        })
                return {"processes": processes, "count": len(processes)}
            except Exception as exc:
                return {"error": str(exc)}

        elif action == "start":
            if not name:
                return {"error": "name is required for start"}
            try:
                proc = subprocess.Popen(
                    name,
                    shell=True,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                )
                return {"pid": proc.pid, "name": name, "status": "started"}
            except Exception as exc:
                return {"error": str(exc), "name": name}

        elif action == "kill":
            if pid is None and not name:
                return {"error": "pid or name is required for kill"}
            try:
                target_pid = pid
                if not target_pid and name:
                    find = subprocess.run(
                        ["pgrep", "-f", name],
                        capture_output=True,
                        text=True,
                        timeout=5,
                    )
                    pids = [int(p) for p in find.stdout.strip().splitlines() if p.strip().isdigit()]
                    target_pid = pids[0] if pids else None
                if target_pid:
                    os.kill(target_pid, 9)
                    return {"pid": target_pid, "status": "killed"}
                return {"error": f"No process found for {name or pid}"}
            except ProcessLookupError:
                return {"error": f"Process {target_pid} not found"}
            except Exception as exc:
                return {"error": str(exc)}

        else:
            return {"error": f"Unknown action: {action}"}


class ServiceTool(Tool):
    """Manage system services."""

    name = "service"
    description = "Install, start, stop, or check status of system services."
    requires_approval = True

    @property
    def schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "enum": ["install", "start", "stop", "status"],
                },
                "name": {"type": "string", "description": "Service name."},
            },
            "required": ["action", "name"],
        }

    def run(self, **kwargs: Any) -> Any:
        action = kwargs.get("action", "status")
        name = kwargs.get("name", "")

        if not name:
            return {"error": "name is required"}

        # systemd-first approach; fall back gracefully on other systems.
        if shutil.which("systemctl"):
            if action == "install":
                cmd = ["sudo", "systemctl", "enable", "--now", name]
            elif action == "start":
                cmd = ["sudo", "systemctl", "start", name]
            elif action == "stop":
                cmd = ["sudo", "systemctl", "stop", name]
            else:
                cmd = ["systemctl", "status", name]
        else:
            if action == "install":
                return {"error": "systemctl not found; cannot install service"}
            cmd = ["service", name, action]

        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            return {
                "service": name,
                "action": action,
                "command": cmd,
                "return_code": result.returncode,
                "stdout": result.stdout,
                "stderr": result.stderr,
            }
        except Exception as exc:
            return {"error": str(exc), "service": name, "action": action}


class ClipboardTool(Tool):
    """Read from or write to the system clipboard."""

    name = "clipboard"
    description = "Read or write the system clipboard."
    requires_approval = False

    @property
    def schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "enum": ["read", "write"],
                    "description": "Clipboard action.",
                },
                "text": {"type": "string", "description": "Text to write (required for write)."},
            },
            "required": ["action"],
        }

    def run(self, **kwargs: Any) -> Any:
        action = kwargs.get("action", "read")
        text = kwargs.get("text", "")

        try:
            if action == "write":
                if not text:
                    return {"error": "text is required for write"}
                try:
                    import pyperclip  # type: ignore[import-untyped]
                    pyperclip.copy(text)
                except ImportError:
                    subprocess.run(["pbcopy"], input=text, text=True)
                return {"status": "written", "size": len(text)}

            elif action == "read":
                try:
                    import pyperclip  # type: ignore[import-untyped]
                    content = pyperclip.paste()
                except ImportError:
                    content = subprocess.run(["pbpaste"], capture_output=True, text=True).stdout
                return {"content": content}

            else:
                return {"error": f"Unknown action: {action}"}
        except Exception as exc:
            return {"error": str(exc)}


class NotifyTool(Tool):
    """Send an OS-level notification."""

    name = "notify"
    description = "Send a native OS notification."
    requires_approval = False

    @property
    def schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "title": {"type": "string", "description": "Notification title."},
                "body": {"type": "string", "description": "Notification body text."},
            },
            "required": ["title"],
        }

    def run(self, **kwargs: Any) -> Any:
        title = kwargs.get("title", "Miori")
        body = kwargs.get("body", "")

        try:
            system = platform.system().lower()
            if system == "darwin":
                subprocess.run(["osascript", "-e", f'display notification "{body}" with title "{title}"'])
            elif system == "linux":
                subprocess.run(["notify-send", title, body])
            elif system == "windows":
                from ctypes import Structure, c_wchar_p, c_int, windll  # type: ignore[attr-defined]
                # Simple toast via powershell
                subprocess.run([
                    "powershell",
                    "-Command",
                    f'[System.Reflection.Assembly]::LoadWithPartialName("System.Windows.Forms"); '
                    f'[System.Windows.Forms.MessageBox]::Show("{body}", "{title}")',
                ])
            else:
                return {"error": f"Notifications not supported on {system}"}
            return {"status": "sent", "title": title, "body": body}
        except Exception as exc:
            logger.error("notify failed: %s", exc)
            return {"error": str(exc)}


class GitTool(Tool):
    """Perform git operations: clone, commit, push, pull."""

    name = "git"
    description = "Perform git operations in a local repository."
    requires_approval = True

    @property
    def schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "enum": ["clone", "commit", "push", "pull"],
                },
                "repo": {"type": "string", "description": "Repository URL (for clone) or path."},
                "message": {"type": "string", "description": "Commit message (for commit)."},
                "cwd": {"type": "string", "description": "Working directory."},
            },
            "required": ["action"],
        }

    def run(self, **kwargs: Any) -> Any:
        action = kwargs.get("action", "status")
        repo = kwargs.get("repo", "")
        message = kwargs.get("message", "Auto-commit by Miori")
        cwd = kwargs.get("cwd") or os.getcwd()

        try:
            if action == "clone":
                if not repo:
                    return {"error": "repo is required for clone"}
                result = subprocess.run(
                    ["git", "clone", repo],
                    capture_output=True,
                    text=True,
                    timeout=120,
                    cwd=cwd,
                )
                return {
                    "action": "clone",
                    "repo": repo,
                    "return_code": result.returncode,
                    "stdout": result.stdout,
                    "stderr": result.stderr,
                }

            subprocess.run(["git", "config", "user.email", "miori@localhost"], cwd=cwd, check=False)
            subprocess.run(["git", "config", "user.name", "Miori"], cwd=cwd, check=False)

            if action == "commit":
                subprocess.run(["git", "add", "."], cwd=cwd, capture_output=True, text=True)
                result = subprocess.run(
                    ["git", "commit", "-m", message],
                    capture_output=True,
                    text=True,
                    cwd=cwd,
                )
                return {
                    "action": "commit",
                    "message": message,
                    "return_code": result.returncode,
                    "stdout": result.stdout,
                    "stderr": result.stderr,
                }

            elif action == "push":
                result = subprocess.run(
                    ["git", "push"],
                    capture_output=True,
                    text=True,
                    timeout=60,
                    cwd=cwd,
                )
                return {
                    "action": "push",
                    "return_code": result.returncode,
                    "stdout": result.stdout,
                    "stderr": result.stderr,
                }

            elif action == "pull":
                result = subprocess.run(
                    ["git", "pull"],
                    capture_output=True,
                    text=True,
                    timeout=60,
                    cwd=cwd,
                )
                return {
                    "action": "pull",
                    "return_code": result.returncode,
                    "stdout": result.stdout,
                    "stderr": result.stderr,
                }

            else:
                return {"error": f"Unknown git action: {action}"}
        except subprocess.TimeoutExpired:
            return {"error": f"Git {action} timed out", "action": action}
        except Exception as exc:
            return {"error": str(exc), "action": action}


class DockerTool(Tool):
    """Interact with Docker: run, stop, list containers."""

    name = "docker"
    description = "Run, stop, or list Docker containers."
    requires_approval = True

    @property
    def schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "enum": ["run", "stop", "ps"],
                    "description": "Docker action.",
                },
                "image": {"type": "string", "description": "Docker image name (for run/stop)."},
                "ports": {
                    "type": "string",
                    "description": "Port mapping, e.g. '8080:80' (for run).",
                },
            },
            "required": ["action"],
        }

    def run(self, **kwargs: Any) -> Any:
        action = kwargs.get("action", "ps")
        image = kwargs.get("image", "")
        ports = kwargs.get("ports", "")

        if not shutil.which("docker"):
            return {"error": "docker is not installed on this system"}

        try:
            if action == "run":
                if not image:
                    return {"error": "image is required for run"}
                cmd = ["docker", "run", "-d"]
                if ports:
                    cmd.extend(["-p", ports])
                cmd.append(image)
                result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
                return {
                    "action": "run",
                    "image": image,
                    "container_id": result.stdout.strip(),
                    "return_code": result.returncode,
                    "stderr": result.stderr,
                }

            elif action == "stop":
                if not image:
                    return {"error": "image is required for stop"}
                result = subprocess.run(
                    ["docker", "stop", image],
                    capture_output=True,
                    text=True,
                    timeout=30,
                )
                return {
                    "action": "stop",
                    "image": image,
                    "return_code": result.returncode,
                    "stdout": result.stdout,
                    "stderr": result.stderr,
                }

            elif action == "ps":
                result = subprocess.run(
                    ["docker", "ps", "-a", "--format", "{{.ID}} {{.Image}} {{.Status}} {{.Names}}"],
                    capture_output=True,
                    text=True,
                    timeout=10,
                )
                lines = [l for l in result.stdout.strip().splitlines() if l.strip()]
                containers = []
                for line in lines:
                    parts = line.split(None, 3)
                    if len(parts) >= 4:
                        containers.append({
                            "id": parts[0],
                            "image": parts[1],
                            "status": parts[2],
                            "name": parts[3],
                        })
                return {"containers": containers, "count": len(containers)}

            else:
                return {"error": f"Unknown docker action: {action}"}
        except Exception as exc:
            return {"error": str(exc), "action": action}

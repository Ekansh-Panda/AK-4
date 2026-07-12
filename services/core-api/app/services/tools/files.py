"""Filesystem tools: read, write, list, delete with undo log."""

from __future__ import annotations

import os
from collections import deque
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app.core.config import settings
from app.core.logging import get_logger
from app.services.tools.base import Tool

logger = get_logger(__name__)

# In-memory ring buffer for undo log (last 100 fs_delete operations).
_undo_log: deque[dict[str, Any]] = deque(maxlen=100)


def _get_undo_log() -> list[dict[str, Any]]:
    return list(_undo_log)


class FsWriteTool(Tool):
    """Write content to a file, supporting overwrite or append mode."""

    name = "fs_write"
    description = "Write content to a file. Supports 'overwrite' or 'append' mode."
    requires_approval = True

    @property
    def schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "Absolute or relative file path."},
                "content": {"type": "string", "description": "Content to write."},
                "mode": {
                    "type": "string",
                    "enum": ["overwrite", "append"],
                    "description": "Write mode: 'overwrite' (default) or 'append'.",
                },
            },
            "required": ["path", "content"],
        }

    def run(self, **kwargs: Any) -> Any:
        file_path = kwargs.get("path", "")
        content = kwargs.get("content", "")
        mode = kwargs.get("mode", "overwrite")

        if not file_path:
            return {"error": "path is required"}

        try:
            path = Path(file_path)
            path.parent.mkdir(parents=True, exist_ok=True)

            write_mode = "a" if mode == "append" else "w"
            with path.open(write_mode, encoding="utf-8") as f:
                f.write(content)

            return {
                "path": str(path.resolve()),
                "mode": mode,
                "size": len(content),
                "status": "success",
            }
        except Exception as exc:
            logger.error("fs_write failed: %s", exc)
            return {"error": str(exc), "path": file_path}


class FsReadTool(Tool):
    """Read content from a file."""

    name = "fs_read"
    description = "Read the content of a file. Returns the full text."
    requires_approval = False

    @property
    def schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "Absolute or relative file path."},
            },
            "required": ["path"],
        }

    def run(self, **kwargs: Any) -> Any:
        file_path = kwargs.get("path", "")

        if not file_path:
            return {"error": "path is required"}

        try:
            path = Path(file_path)
            if not path.exists():
                return {"error": f"File not found: {file_path}"}

            content = path.read_text(encoding="utf-8")
            return {
                "path": str(path.resolve()),
                "size": len(content),
                "content": content,
            }
        except Exception as exc:
            logger.error("fs_read failed: %s", exc)
            return {"error": str(exc), "path": file_path}


class FsListTool(Tool):
    """List directory contents."""

    name = "fs_list"
    description = "List files and directories in a given path."
    requires_approval = False

    @property
    def schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "Directory path to list. Defaults to current directory.",
                },
                "recursive": {
                    "type": "boolean",
                    "description": "Whether to list recursively. Default false.",
                },
            },
            "required": [],
        }

    def run(self, **kwargs: Any) -> Any:
        dir_path = kwargs.get("path", ".")
        recursive = kwargs.get("recursive", False)

        try:
            path = Path(dir_path)
            if not path.exists():
                return {"error": f"Path not found: {dir_path}"}

            entries = []
            if recursive:
                for root, dirs, files in os.walk(path):
                    for name in sorted(dirs + files):
                        full = Path(root) / name
                        entries.append({
                            "name": name,
                            "path": str(full.relative_to(path)),
                            "is_dir": full.is_dir(),
                            "size": full.stat().st_size if full.is_file() else None,
                        })
            else:
                for child in sorted(path.iterdir(), key=lambda p: (p.is_file(), p.name.lower())):
                    entries.append({
                        "name": child.name,
                        "path": str(child),
                        "is_dir": child.is_dir(),
                        "size": child.stat().st_size if child.is_file() else None,
                    })

            return {
                "path": str(path.resolve()),
                "entries": entries,
                "count": len(entries),
            }
        except Exception as exc:
            logger.error("fs_list failed: %s", exc)
            return {"error": str(exc), "path": dir_path}


class FsDeleteTool(Tool):
    """Delete a file, recording content in the undo log."""

    name = "fs_delete"
    description = (
        "Delete a file. The deleted file's content is recorded in the in-memory undo log "
        "(last 100 deletions) so it can be recovered."
    )
    requires_approval = True

    @property
    def schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "Absolute or relative file path to delete."},
            },
            "required": ["path"],
        }

    def run(self, **kwargs: Any) -> Any:
        file_path = kwargs.get("path", "")

        if not file_path:
            return {"error": "path is required"}

        try:
            path = Path(file_path)
            if not path.exists():
                return {"error": f"File not found: {file_path}"}

            if not path.is_file():
                return {"error": f"Not a file: {file_path}"}

            resolved_path = str(path.resolve())
            content = path.read_text(encoding="utf-8")
            path.unlink()

            undo_entry = {
                "path": resolved_path,
                "content": content,
                "ts": datetime.now(timezone.utc).isoformat(),
            }
            _undo_log.append(undo_entry)

            return {
                "path": resolved_path,
                "size": len(content),
                "status": "deleted",
                "undo_log_size": len(_undo_log),
            }
        except Exception as exc:
            logger.error("fs_delete failed: %s", exc)
            return {"error": str(exc), "path": file_path}


def get_undo_log() -> list[dict[str, Any]]:
    """Expose the in-memory undo log for inspection/recovery."""
    return _get_undo_log()

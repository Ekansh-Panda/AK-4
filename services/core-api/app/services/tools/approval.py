"""Tool execution approval mechanism."""

from __future__ import annotations

import asyncio
from typing import Any

# Map of tool_call_id -> asyncio.Future
_pending_approvals: dict[str, asyncio.Future[bool]] = {}

def register_pending_approval(tool_call_id: str) -> asyncio.Future[bool]:
    """Register a tool call ID and return a future that resolves to True/False."""
    future = asyncio.Future()
    _pending_approvals[tool_call_id] = future
    return future

def resolve_approval(tool_call_id: str, approved: bool) -> bool:
    """Resolve a pending tool call. Returns True if found and resolved, False otherwise."""
    future = _pending_approvals.pop(tool_call_id, None)
    if future and not future.done():
        future.set_result(approved)
        return True
    return False

def get_pending_calls() -> list[str]:
    """Return a list of currently pending tool call IDs."""
    return list(_pending_approvals.keys())

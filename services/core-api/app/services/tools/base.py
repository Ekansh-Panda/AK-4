"""Tool abstraction.

A Tool is a named, schema-described callable the model can invoke.

TODO(computer-use): add a sandboxed tool category for screen/keyboard/mouse
control and file-system actions, gated behind explicit user consent.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class Tool(ABC):
    """Base class for all tools."""

    #: Unique tool name used for invocation.
    name: str = "tool"
    #: Human / model readable description.
    description: str = ""
    #: Whether this tool requires explicit user approval before execution.
    requires_approval: bool = False

    @property
    def schema(self) -> dict[str, Any]:
        """JSON-schema-ish description of accepted parameters.

        Override in subclasses. Default declares no parameters.
        """
        return {"type": "object", "properties": {}, "required": []}

    @abstractmethod
    def run(self, **kwargs: Any) -> Any:
        """Execute the tool and return a JSON-serializable result."""

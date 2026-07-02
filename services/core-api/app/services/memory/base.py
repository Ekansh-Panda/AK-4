"""Abstract memory provider interface.

Providers persist and retrieve memories. The default lite provider uses plain
SQLite text matching. Heavy providers (vector retrieval) plug in behind the
same interface.

TODO(Odysseus/Khoj): implement a vector-backed provider (embeddings + ANN
search) that subclasses ``MemoryProvider`` and is selected when LITE_MODE is
disabled.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class MemoryItem:
    """Transport object decoupled from the ORM model."""

    id: str
    namespace: str
    content: str
    user_id: str | None = None
    meta: str | None = None
    pinned: bool = False
    score: float = 0.0


class MemoryProvider(ABC):
    """Interface every memory backend must implement."""

    name: str = "base"

    @abstractmethod
    async def add(
        self,
        content: str,
        *,
        namespace: str = "default",
        user_id: str | None = None,
        meta: str | None = None,
        pinned: bool = False,
    ) -> MemoryItem:
        """Store a memory and return it."""

    @abstractmethod
    async def search(
        self, query: str, *, namespace: str = "default", limit: int = 10
    ) -> list[MemoryItem]:
        """Return memories relevant to ``query`` (best-effort)."""

    @abstractmethod
    def list(
        self,
        *,
        kind: str | None = None,
        pinned: bool | None = None,
        limit: int = 50,
    ) -> list[MemoryItem]:
        """Return recent memories, optionally filtered by kind/pinned."""

    @abstractmethod
    def get(self, memory_id: str) -> MemoryItem | None:
        """Fetch a memory by id."""

    @abstractmethod
    def update(
        self,
        memory_id: str,
        *,
        content: str | None = None,
        pinned: bool | None = None,
    ) -> MemoryItem | None:
        """Edit content and/or toggle pinned; return the updated item."""

    @abstractmethod
    def delete(self, memory_id: str) -> bool:
        """Delete a memory; return True if something was removed."""

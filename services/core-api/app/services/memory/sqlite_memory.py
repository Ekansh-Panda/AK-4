"""Default lite memory provider backed by SQLite.

Uses simple substring matching for ``search`` — good enough for v0.1 and keeps
Miori usable on low-end machines without embeddings.

TODO(Odysseus/Khoj): replace substring search with semantic vector retrieval
when LITE_MODE is off.
"""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.memory import Memory
from app.services.memory.base import MemoryItem, MemoryProvider


def _to_item(row: Memory, score: float = 0.0) -> MemoryItem:
    return MemoryItem(
        id=row.id,
        namespace=row.namespace,
        content=row.content,
        user_id=row.user_id,
        meta=row.meta,
        pinned=bool(row.pinned),
        score=score,
    )


class SqliteMemoryProvider(MemoryProvider):
    name = "sqlite-lite"

    def __init__(self, db: Session) -> None:
        self._db = db

    async def add(
        self,
        content: str,
        *,
        namespace: str = "default",
        user_id: str | None = None,
        meta: str | None = None,
        pinned: bool = False,
    ) -> MemoryItem:
        row = Memory(
            content=content,
            namespace=namespace,
            user_id=user_id,
            meta=meta,
            pinned=pinned,
        )
        self._db.add(row)
        self._db.commit()
        self._db.refresh(row)
        return _to_item(row)

    async def search(
        self, query: str, *, namespace: str = "default", limit: int = 10
    ) -> list[MemoryItem]:
        if namespace.endswith("%"):
            stmt = select(Memory).where(Memory.namespace.like(namespace))
        else:
            stmt = select(Memory).where(Memory.namespace == namespace)

        stmt = (
            stmt.where(Memory.content.ilike(f"%{query}%"))
            .order_by(Memory.created_at.desc())
            .limit(limit)
        )
        rows = self._db.execute(stmt).scalars().all()
        # Naive score: 1.0 for any match. TODO: real relevance scoring.
        return [_to_item(r, score=1.0) for r in rows]

    def list(
        self,
        *,
        kind: str | None = None,
        pinned: bool | None = None,
        limit: int = 50,
    ) -> list[MemoryItem]:
        stmt = select(Memory)
        if kind is not None:
            stmt = stmt.where(Memory.namespace == kind)
        if pinned is not None:
            stmt = stmt.where(Memory.pinned == pinned)
        # Pinned first, then recency.
        stmt = stmt.order_by(Memory.pinned.desc(), Memory.created_at.desc()).limit(limit)
        rows = self._db.execute(stmt).scalars().all()
        return [_to_item(r) for r in rows]

    def get(self, memory_id: str) -> MemoryItem | None:
        row = self._db.get(Memory, memory_id)
        return _to_item(row) if row else None

    def update(
        self,
        memory_id: str,
        *,
        content: str | None = None,
        pinned: bool | None = None,
    ) -> MemoryItem | None:
        row = self._db.get(Memory, memory_id)
        if not row:
            return None
        if content is not None:
            row.content = content
        if pinned is not None:
            row.pinned = pinned
        self._db.commit()
        self._db.refresh(row)
        return _to_item(row)

    def delete(self, memory_id: str) -> bool:
        row = self._db.get(Memory, memory_id)
        if not row:
            return False
        self._db.delete(row)
        self._db.commit()
        return True

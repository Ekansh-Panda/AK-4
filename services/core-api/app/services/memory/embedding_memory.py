"""Semantic memory provider (cosine similarity).

Used when LITE_MODE is off AND SEMANTIC_MEMORY_ENABLED is true. Embeddings are computed
via the active model provider (falling back to substring match if embeddings are unsupported).
"""

from __future__ import annotations

import json

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.logging import get_logger
from app.models.memory import Memory
from app.services.memory.base import MemoryItem
from app.services.memory.sqlite_memory import SqliteMemoryProvider, _to_item

logger = get_logger(__name__)

class EmbeddingMemoryProvider(SqliteMemoryProvider):
    name = "embedding"

    def __init__(self, db: Session) -> None:
        super().__init__(db)

    # --- embedding helpers ---
    async def _embed_one(self, text: str) -> list[float] | None:
        from app.services.providers.registry import registry
        provider = registry.get()
        if provider.available():
            try:
                embeddings = await provider.embed([text])
                if embeddings and len(embeddings) > 0:
                    return embeddings[0]
            except NotImplementedError:
                logger.debug("Provider %s does not support embeddings", provider.name)
            except Exception as exc:
                logger.warning("Provider embed failed: %s", exc)
        return None

    # --- writes ---
    async def add(
        self,
        content: str,
        *,
        namespace: str = "default",
        user_id: str | None = None,
        meta: str | None = None,
        pinned: bool = False,
    ) -> MemoryItem:
        embedding = None
        vec = await self._embed_one(content)
        if vec is not None:
            embedding = json.dumps(vec)
        
        row = Memory(
            content=content,
            namespace=namespace,
            user_id=user_id,
            meta=meta,
            pinned=pinned,
            embedding=embedding,
        )
        self._db.add(row)
        self._db.commit()
        self._db.refresh(row)
        return _to_item(row)

    # --- semantic search ---
    async def search(
        self, query: str, *, namespace: str = "default", limit: int = 10
    ) -> list[MemoryItem]:
        import numpy as np  # lazy

        if namespace.endswith("%"):
            stmt = select(Memory).where(Memory.namespace.like(namespace))
        else:
            stmt = select(Memory).where(Memory.namespace == namespace)
            
        rows = list(self._db.execute(stmt).scalars())
        if not rows:
            return []

        vec = await self._embed_one(query)
        if vec is None:
            return await super().search(query, namespace=namespace, limit=limit)

        try:
            q = np.asarray(vec, dtype="float32")
        except Exception as exc:  # noqa: BLE001 - degrade to substring
            logger.warning("query embed array cast failed (%s); substring fallback", exc)
            return await super().search(query, namespace=namespace, limit=limit)

        scored: list[tuple[float, Memory]] = []
        for r in rows:
            if not r.embedding:
                continue
            try:
                v = np.asarray(json.loads(r.embedding), dtype="float32")
            except (json.JSONDecodeError, TypeError, ValueError):
                continue
            denom = float(np.linalg.norm(q) * np.linalg.norm(v))
            if denom == 0.0:
                continue
            scored.append((float(np.dot(q, v) / denom), r))

        if not scored:
            # Nothing embedded yet (e.g. pre-existing lite rows) — substring.
            return await super().search(query, namespace=namespace, limit=limit)

        scored.sort(key=lambda t: t[0], reverse=True)
        return [_to_item(r, score=s) for s, r in scored[:limit]]

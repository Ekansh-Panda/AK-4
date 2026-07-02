"""MemoryService — wires a concrete MemoryProvider to the rest of the app.

Selects the provider based on config (lite vs heavy). For now only the SQLite
lite provider exists. Also hosts the conversation-summarization hook used by
ChatService.
"""

from __future__ import annotations

import json

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.logging import get_logger
from app.services.memory.base import MemoryItem, MemoryProvider
from app.services.memory.sqlite_memory import SqliteMemoryProvider

logger = get_logger(__name__)

SUMMARY_KIND = "summary"


class MemoryService:
    def __init__(self, db: Session, provider: MemoryProvider | None = None) -> None:
        self._db = db
        self._provider = provider or self._select_provider(db)

    @staticmethod
    def _select_provider(db: Session) -> MemoryProvider:
        # Runtime DB setting "lite_mode" overrides the env default (Task 1.3).
        from app.core.config import get_effective_bool
        from app.services.settings_service import LITE_MODE_KEY

        lite = get_effective_bool(db, LITE_MODE_KEY, settings.LITE_MODE)
        semantic_enabled = get_effective_bool(db, "semantic_memory_enabled", settings.SEMANTIC_MEMORY_ENABLED)

        if lite or not semantic_enabled:
            return SqliteMemoryProvider(db)
        
        # Heavy path: semantic embedding memory.
        try:
            from app.services.memory.embedding_memory import EmbeddingMemoryProvider
            return EmbeddingMemoryProvider(db)
        except Exception as exc:  # noqa: BLE001 - optional heavy dep absent
            logger.info("Embedding memory unavailable (%s); using sqlite-lite", exc)
            return SqliteMemoryProvider(db)

    @property
    def provider_name(self) -> str:
        return self._provider.name

    async def add(
        self,
        content: str,
        *,
        namespace: str = "default",
        user_id: str | None = None,
        meta: str | None = None,
        pinned: bool = False,
    ) -> MemoryItem:
        return await self._provider.add(
            content, namespace=namespace, user_id=user_id, meta=meta, pinned=pinned
        )

    async def search(
        self, query: str, *, namespace: str = "default", limit: int = 10
    ) -> list[MemoryItem]:
        return await self._provider.search(query, namespace=namespace, limit=limit)

    def list(
        self,
        *,
        kind: str | None = None,
        pinned: bool | None = None,
        limit: int = 50,
    ) -> list[MemoryItem]:
        return self._provider.list(kind=kind, pinned=pinned, limit=limit)

    def get(self, memory_id: str) -> MemoryItem | None:
        return self._provider.get(memory_id)

    def update(
        self,
        memory_id: str,
        *,
        content: str | None = None,
        pinned: bool | None = None,
    ) -> MemoryItem | None:
        return self._provider.update(memory_id, content=content, pinned=pinned)

    def delete(self, memory_id: str) -> bool:
        return self._provider.delete(memory_id)

    # --- summarization hook ---
    async def summarize_session(self, session_id: str) -> MemoryItem | None:
        """Summarize a session's messages and store it as a ``summary`` memory.

        Uses the active model provider when available; otherwise a cheap
        heuristic (first/last user lines + counts). Best-effort: returns None on
        empty sessions. Errors are the caller's to swallow.
        """
        from app.models.message import Message

        rows = list(
            self._db.execute(
                select(Message)
                .where(Message.session_id == session_id)
                .order_by(Message.created_at)
            )
            .scalars()
            .all()
        )
        if not rows:
            return None

        summary = await self._compose_summary(rows)
        meta = json.dumps({"session_id": session_id})
        return await self.add(summary, namespace=SUMMARY_KIND, meta=meta)

    async def _compose_summary(self, rows: list) -> str:
        user_lines = [r.content for r in rows if r.role == "user"]
        n_user = len(user_lines)
        n_assistant = sum(1 for r in rows if r.role == "assistant")

        # Try the active provider for a real summary.
        try:
            from app.services.providers.base import ChatMessage
            from app.services.providers.registry import registry as provider_registry

            provider = provider_registry.get()
            if provider.available() and provider.name != "mock":
                transcript = "\n".join(
                    f"{r.role}: {r.content}" for r in rows[-40:]
                )
                msgs = [
                    ChatMessage(
                        role="user",
                        content=(
                            "Summarize this conversation in 2-3 sentences, "
                            "capturing key facts and the user's intent:\n\n"
                            + transcript
                        ),
                    )
                ]
                text = await provider.chat(
                    msgs, system_prompt="You write concise conversation summaries."
                )
                if text and text.strip():
                    return text.strip()
        except Exception as exc:  # noqa: BLE001 - fall through to heuristic
            logger.debug("Provider summary failed, using heuristic: %s", exc)

        # Heuristic fallback.
        first = user_lines[0][:160] if user_lines else "(no user messages)"
        last = user_lines[-1][:160] if user_lines else ""
        parts = [
            f"Conversation with {n_user} user / {n_assistant} assistant messages.",
            f"Started with: {first}",
        ]
        if last and last != first:
            parts.append(f"Most recently: {last}")
        return " ".join(parts)

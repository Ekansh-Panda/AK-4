"""PersonaEvolutionService — distills a user's evolving preferences over time.

Every ``EVOLVE_EVERY_TURNS`` assistant turns (or once ``EVOLVE_MAX_AGE`` has
elapsed since the last evolution) this service summarizes the user's stable
preferences, recurring corrections and style signals into a single compact
block. The block is stored as a ``persona:evolution`` memory and later appended
to the system prompt by :class:`~app.services.persona.service.PersonaService` so
Miori adapts to the user over time.

The service is stateless: every trigger reads and writes the memory table only,
so it works across sessions, processes and restarts without in-memory state.
Best-effort throughout — any failure degrades to "no evolution this turn" and
never breaks a chat turn.
"""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.logging import get_logger
from app.services.memory.base import MemoryItem
from app.services.memory.service import MemoryService

logger = get_logger(__name__)

# Memory kind (namespace) under which evolution blocks are stored.
EVOLUTION_KIND = "persona:evolution"
# Kind holding the cheap heuristic facts captured by ChatService.
FACTS_KIND = "user:facts"

# Trigger cadence: whichever comes first.
EVOLVE_EVERY_TURNS = 10
EVOLVE_MAX_AGE = timedelta(hours=24)

# Keep the appended block tight so it costs almost nothing in the prompt.
MAX_BLOCK_CHARS = 200
# How many recent messages to feed the summarizer.
TRANSCRIPT_TURNS = 40


class PersonaEvolutionService:
    """Distill and persist a user's preferences as a ``persona:evolution`` block."""

    # Exposed so callers (e.g. PersonaService) can reference the kind.
    EVOLUTION_KIND = EVOLUTION_KIND

    async def evolve(
        self, user_id: str, session_id: str, db: Session
    ) -> str | None:
        """Return a fresh compact evolution block, or ``None``.

        Returns ``None`` when it is not yet time to evolve, when there is nothing
        worth summarizing, or when no real provider is available and no heuristic
        signal exists. On success the block is persisted as a ``persona:evolution``
        memory before being returned.
        """
        try:
            mem = MemoryService(db)

            n_turns = self._assistant_turns(db, session_id)
            previous = self._latest_evolution(mem, user_id)
            if not self._is_due(n_turns, previous):
                return None

            block = await self._summarize(db, mem, user_id, session_id, previous)
            if not block:
                return None
            block = block.strip()[:MAX_BLOCK_CHARS].strip()
            if not block:
                return None

            meta = json.dumps(
                {
                    "session_id": session_id,
                    "turns": n_turns,
                    "ts": datetime.now(timezone.utc).isoformat(),
                }
            )
            await mem.add(
                block, namespace=EVOLUTION_KIND, user_id=user_id, meta=meta
            )
            return block
        except Exception as exc:  # noqa: BLE001 - non-blocking, best-effort
            logger.debug("persona evolution skipped: %s", exc)
            return None

    # --- trigger accounting ---
    @staticmethod
    def _assistant_turns(db: Session, session_id: str) -> int:
        from app.models.message import Message

        return db.execute(
            select(func.count())
            .select_from(Message)
            .where(Message.session_id == session_id)
            .where(Message.role == "assistant")
        ).scalar_one()

    @staticmethod
    def _latest_evolution(
        mem: MemoryService, user_id: str | None
    ) -> MemoryItem | None:
        """Most recent evolution block for ``user_id`` (list is recency-ordered)."""
        for item in mem.list(kind=EVOLUTION_KIND, limit=50):
            if user_id is None or item.user_id is None or item.user_id == user_id:
                return item
        return None

    @classmethod
    def _is_due(cls, n_turns: int, previous: MemoryItem | None) -> bool:
        """Whether a new evolution should be produced now."""
        if previous is None:
            return n_turns >= EVOLVE_EVERY_TURNS
        last_turns, last_ts = cls._parse_meta(previous.meta)
        if last_ts is not None:
            if (datetime.now(timezone.utc) - last_ts) >= EVOLVE_MAX_AGE:
                return True
        if last_turns is not None:
            return (n_turns - last_turns) >= EVOLVE_EVERY_TURNS
        return n_turns >= EVOLVE_EVERY_TURNS

    @staticmethod
    def _parse_meta(meta: str | None) -> tuple[int | None, datetime | None]:
        if not meta:
            return None, None
        try:
            data = json.loads(meta)
        except (TypeError, ValueError):
            return None, None
        turns = data.get("turns")
        ts_raw = data.get("ts")
        ts: datetime | None = None
        if isinstance(ts_raw, str):
            try:
                ts = datetime.fromisoformat(ts_raw)
                if ts.tzinfo is None:
                    ts = ts.replace(tzinfo=timezone.utc)
            except ValueError:
                ts = None
        return (turns if isinstance(turns, int) else None), ts

    # --- summarization ---
    async def _summarize(
        self,
        db: Session,
        mem: MemoryService,
        user_id: str | None,
        session_id: str,
        previous: MemoryItem | None,
    ) -> str | None:
        facts = mem.list(kind=FACTS_KIND, limit=20)
        fact_lines = [
            f.content
            for f in facts
            if user_id is None or f.user_id is None or f.user_id == user_id
        ]
        transcript = self._recent_transcript(db, session_id)

        block = await self._provider_summary(fact_lines, transcript, previous)
        if block:
            return block
        # Graceful offline fallback: reuse captured facts / prior block.
        return self._heuristic_summary(fact_lines, previous)

    @staticmethod
    def _recent_transcript(db: Session, session_id: str) -> str:
        from app.models.message import Message

        rows = list(
            db.execute(
                select(Message)
                .where(Message.session_id == session_id)
                .order_by(Message.created_at.desc())
                .limit(TRANSCRIPT_TURNS)
            )
            .scalars()
            .all()
        )
        rows.reverse()
        return "\n".join(f"{r.role}: {r.content}" for r in rows)

    @staticmethod
    async def _provider_summary(
        fact_lines: list[str],
        transcript: str,
        previous: MemoryItem | None,
    ) -> str | None:
        """Summarize preferences with the active LLM, or ``None`` if unavailable."""
        try:
            from app.services.providers.base import ChatMessage
            from app.services.providers.registry import registry

            provider = registry.get()
            # Skip gracefully when no real provider is configured.
            if not provider.available() or provider.name == "mock":
                return None

            parts: list[str] = []
            if previous is not None and previous.content:
                parts.append("Previous notes about the user:\n" + previous.content)
            if fact_lines:
                parts.append(
                    "Known facts:\n" + "\n".join(f"- {f}" for f in fact_lines)
                )
            if transcript:
                parts.append("Recent conversation:\n" + transcript)
            if not parts:
                return None

            prompt = (
                "From the material below, distill this user's STABLE preferences, "
                "recurring corrections and communication style into ONE compact "
                "block under 200 characters. Use terse statements, e.g. 'User "
                "prefers concise answers. User likes technical depth. User "
                "corrects: use list format for steps.' Output only the block.\n\n"
                + "\n\n".join(parts)
            )
            text = await provider.chat(
                [ChatMessage(role="user", content=prompt)],
                system_prompt=(
                    "You maintain a tight, evolving profile of a user's "
                    "preferences and communication style."
                ),
            )
            if isinstance(text, str) and text.strip():
                return text.strip()
        except Exception as exc:  # noqa: BLE001 - fall through to heuristic
            logger.debug("provider persona summary failed: %s", exc)
        return None

    @staticmethod
    def _heuristic_summary(
        fact_lines: list[str], previous: MemoryItem | None
    ) -> str | None:
        """Cheap offline block built from captured preference-style facts."""
        prefs = [
            f
            for f in fact_lines
            if any(k in f.lower() for k in ("prefer", "like", "dislike", "hate"))
        ]
        source = prefs or fact_lines
        if not source:
            return previous.content if previous is not None else None
        return " ".join(source[:3])

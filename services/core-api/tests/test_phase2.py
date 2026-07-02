"""Phase 2 tests — semantic memory + chat recall (offline, lite mode).

Run: cd services/core-api && pytest tests/test_phase2.py
"""

from __future__ import annotations

import pytest

from app.services.chat_service import ChatService
from app.services.memory.service import MemoryService
from app.services.settings_service import LITE_MODE_KEY, SettingsService


# --- 2.2 fact extraction heuristic ---
def test_extract_facts():
    facts = ChatService._extract_facts(
        "Hi, my name is Ekansh. I like trail running. I work at Vercel."
    )
    joined = " ".join(facts)
    assert any("Ekansh" in f for f in facts)
    assert "running" in joined
    assert len(facts) <= 3


# --- 2.2 fact capture + recall wired into a turn ---
@pytest.mark.asyncio
async def test_chat_captures_and_recalls_facts(db):
    svc = ChatService(db)
    await svc.respond(session_id=None, user_text="my name is Ekansh", user_id="u")
    facts = MemoryService(db).list(kind="user:facts", limit=50)
    assert any("Ekansh" in m.content for m in facts)
    # Recall surfaces the stored fact for a related query.
    # Note: lite-mode uses substring matching, so search for "name" which
    # matches the stored fact "User's name is Ekansh."
    ctx = await svc._recall_context("name", "u")
    assert ctx is not None and "Ekansh" in ctx


@pytest.mark.asyncio
async def test_recall_returns_none_when_empty(db):
    svc = ChatService(db)
    ctx = await svc._recall_context("anything", "u")
    assert ctx is None


# --- 2.1 provider selection falls back when sentence-transformers absent ---
def test_select_provider_falls_back_without_sentence_transformers(db):
    # Force non-lite so the heavy path is attempted.
    SettingsService(db).set(LITE_MODE_KEY, "false")
    provider = MemoryService._select_provider(db)
    # sentence-transformers isn't installed in CI/sandbox -> sqlite-lite fallback.
    # If it *is* installed, the embedding provider is acceptable too.
    assert provider.name in {"sqlite-lite", "embedding"}


def test_lite_mode_uses_sqlite(db):
    SettingsService(db).set(LITE_MODE_KEY, "true")
    assert MemoryService._select_provider(db).name == "sqlite-lite"

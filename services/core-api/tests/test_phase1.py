"""Phase 1 regression tests (offline, mock provider only).

Run: cd services/core-api && pytest tests/test_phase1.py
"""

from __future__ import annotations

import asyncio

from sqlalchemy import select

from app.core.auth import DEV_USER_ID
from app.models.message import Message
from app.services.chat_service import ChatService
from app.services.persona.service import PersonaService
from app.services.providers.registry import ProviderRegistry
from app.services.providers.mock_provider import MockProvider


def _roles(db, session_id) -> list[str]:
    return [
        m.role
        for m in db.execute(
            select(Message).where(Message.session_id == session_id).order_by(Message.created_at)
        ).scalars()
    ]


# --- 1.1: no duplicate user message ---
def test_no_duplicate_user_message(db):
    svc = ChatService(db)
    session, _ = asyncio.run(svc.respond(session_id=None, user_text="hi", user_id="u"))
    # Turn 1 persists exactly one user + one assistant (not two users).
    assert _roles(db, session.id) == ["user", "assistant"]
    # Provider-visible history has exactly one user entry (the dup bug appended a 2nd).
    msgs = svc._build_provider_messages(session.id)
    assert [m.role for m in msgs].count("user") == 1
    # Turn 2 stays strictly alternating.
    asyncio.run(svc.respond(session_id=session.id, user_text="again", user_id="u"))
    assert _roles(db, session.id) == ["user", "assistant", "user", "assistant"]


# --- 1.2: persona mode is per-session, not global ---
def test_persona_mode_is_per_session(db):
    svc = ChatService(db)
    a, _ = asyncio.run(
        svc.respond(session_id=None, user_text="x", persona_mode="coder", user_id="u")
    )
    b, _ = asyncio.run(svc.respond(session_id=None, user_text="y", user_id="u"))
    db.refresh(a)
    db.refresh(b)
    assert a.persona_mode == "coder"
    assert b.persona_mode == "friend"  # default, unaffected by the other session


def test_persona_service_is_stateless():
    assert not hasattr(PersonaService, "set_mode")
    p = PersonaService()
    assert "Miori" in p.build_prompt("friend")
    assert p.normalize_mode("nonsense") == "friend"


# --- 1.4: user scoping ---
def test_user_cannot_access_other_users_session(db):
    svc = ChatService(db)
    session, _ = asyncio.run(
        svc.respond(session_id=None, user_text="secret", user_id="userA")
    )
    assert svc.get_owned_session(session.id, "userA") is not None
    assert svc.get_owned_session(session.id, "userB") is None


def test_get_current_user_stub():
    from app.core.auth import get_current_user

    assert get_current_user() == DEV_USER_ID


# --- 1.5: provider registry fallback ---
def test_registry_returns_configured_and_falls_back(db):
    reg = ProviderRegistry()
    reg.register(MockProvider(), default=True)

    class _Keyed(MockProvider):
        name = "keyed"

        def __init__(self, ok):
            self._ok = ok

        def available(self):
            return self._ok

    reg.register(_Keyed(True))
    reg.set_active("keyed")
    assert reg.get().name == "keyed"  # configured -> returned

    reg2 = ProviderRegistry()
    reg2.register(MockProvider(), default=True)
    reg2.register(_Keyed(False))
    reg2.set_active("keyed")
    assert reg2.get().name == "mock"  # unconfigured -> mock fallback


def test_all_eight_providers_registered():
    from app.services.providers.registry import registry

    names = {p.name for p in registry.list()}
    for expected in {
        "mock", "openai", "gemini", "groq", "mistral",
        "sambanova", "openrouter", "huggingface", "cohere", "cloudflare",
    }:
        assert expected in names


# --- 1.3: lite_mode runtime resolver ---
def test_effective_bool_db_overrides_env(db):
    from app.core.config import get_effective_bool
    from app.services.settings_service import LITE_MODE_KEY, SettingsService

    assert get_effective_bool(db, LITE_MODE_KEY, True) is True  # no row -> default
    SettingsService(db).set(LITE_MODE_KEY, "false")
    assert get_effective_bool(db, LITE_MODE_KEY, True) is False  # DB overrides env

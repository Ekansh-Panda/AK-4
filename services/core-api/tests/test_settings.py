"""SettingsService get/set round-trip against in-memory SQLite."""

from __future__ import annotations

from app.services.settings_service import ACTIVE_PROVIDER_KEY, SettingsService


def test_get_default_when_absent(db):
    svc = SettingsService(db)
    assert svc.get("nope", default="fallback") == "fallback"


def test_set_then_get(db):
    svc = SettingsService(db)
    svc.set(ACTIVE_PROVIDER_KEY, "openai")
    assert svc.get(ACTIVE_PROVIDER_KEY) == "openai"


def test_set_overwrites(db):
    svc = SettingsService(db)
    svc.set("k", "v1")
    svc.set("k", "v2")
    assert svc.get("k") == "v2"

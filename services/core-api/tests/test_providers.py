"""Provider registry falls back to mock when no key is configured."""

from __future__ import annotations

from app.services.providers.base import ChatMessage
from app.services.providers.gemini import GeminiProvider
from app.services.providers.mock_provider import MockProvider
from app.services.providers.openai_compatible import OpenAICompatibleProvider
from app.services.providers.registry import ProviderRegistry


def _registry_without_keys() -> ProviderRegistry:
    reg = ProviderRegistry()
    reg.register(MockProvider(), default=True)
    reg.register(OpenAICompatibleProvider(api_key=None))
    reg.register(GeminiProvider(api_key=None))
    return reg


def test_unconfigured_providers_report_unavailable():
    assert OpenAICompatibleProvider(api_key=None).available() is False
    assert GeminiProvider(api_key=None).available() is False
    assert MockProvider().available() is True


def test_get_falls_back_to_mock_when_active_has_no_key():
    reg = _registry_without_keys()
    reg.set_active("openai")  # selected, but no key
    provider = reg.get()
    assert provider.name == "mock"


def test_get_named_returns_requested_provider():
    reg = _registry_without_keys()
    assert reg.get("gemini").name == "gemini"


def test_availability_lists_all_providers():
    reg = _registry_without_keys()
    names = {a.name for a in reg.availability()}
    assert names == {"mock", "openai", "gemini"}


def test_mock_chat_echoes():
    import asyncio

    provider = MockProvider()
    reply = asyncio.run(
        provider.chat([ChatMessage(role="user", content="hi there")])
    )
    assert "hi there" in reply

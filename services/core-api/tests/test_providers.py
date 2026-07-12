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


# --- Module 9: rate-limit + provider resilience ---

class _FakeResponse:
    def __init__(self, status_code: int, retry_after: str | None = None):
        self.status_code = status_code
        self.headers = {"Retry-After": retry_after} if retry_after is not None else {}


class _StatusError(Exception):
    def __init__(self, status_code: int, retry_after: str | None = None):
        super().__init__(f"status {status_code}")
        self.response = _FakeResponse(status_code, retry_after)


class FlakyProvider(MockProvider):
    """Emits ``failures`` then succeeds, or always fails with ``error``."""

    def __init__(self, *, failures=0, error=None, name="flaky"):
        super().__init__()
        self.name = name
        self._failures = failures
        self._error = error
        self.calls = 0

    async def chat(self, messages, *, model=None, system_prompt=None, tools=None):
        self.calls += 1
        if self._failures > 0:
            self._failures -= 1
            raise self._error
        if self._error is not None and self._failures == 0:
            raise self._error
        return await super().chat(messages, model=model, system_prompt=system_prompt, tools=tools)


def test_retry_backoff_on_429_then_success():
    import asyncio

    # Fails twice with 429, then succeeds -> sleeps 1s then 2s.
    provider = FlakyProvider(failures=2, error=_StatusError(429))
    result = asyncio.run(
        provider.chat_with_retry([ChatMessage(role="user", content="hi")], max_retries=3)
    )
    assert "hi" in result
    assert provider.calls == 3


def test_no_retry_on_auth_error():
    import asyncio

    provider = FlakyProvider(failures=5, error=_StatusError(401))
    try:
        asyncio.run(
            provider.chat_with_retry([ChatMessage(role="user", content="hi")], max_retries=3)
        )
        assert False, "expected 401 to be raised without retry"
    except _StatusError as exc:
        assert exc.response.status_code == 401
    # Should not have retried past the first failure.
    assert provider.calls == 1


def test_retry_after_header_is_parsed():
    provider = FlakyProvider(failures=1, error=_StatusError(429, retry_after="7"))
    delay = provider._extract_retry_after(_StatusError(429, retry_after="7"))
    assert delay == 7.0
    # Backoff uses the explicit header value.
    assert provider._retry_delay(0, _StatusError(429, retry_after="7")) == 7.0


def test_fallback_chain_reaches_mock_on_429():
    import asyncio

    reg = ProviderRegistry()
    reg.register(MockProvider(), default=True)
    reg.register(FlakyProvider(failures=5, error=_StatusError(429), name="flaky"))
    reg.set_active("flaky")  # selected but always 429s

    result = asyncio.run(
        reg.chat_with_fallback([ChatMessage(role="user", content="hello")])
    )
    assert "hello" in result
    # Final answer came from the mock provider, never failing the user.
    assert reg.last_fallback_provider == "mock"


def test_fallback_uses_next_available_provider():
    import asyncio

    class SecondProvider(MockProvider):
        name = "second"

    reg = ProviderRegistry()
    reg.register(MockProvider(), default=True)
    # primary always 429s, second works -> second should serve, not mock.
    reg.register(FlakyProvider(failures=5, error=_StatusError(429), name="flaky"))
    reg.register(SecondProvider())
    reg.set_active("flaky")

    result = asyncio.run(
        reg.chat_with_fallback([ChatMessage(role="user", content="hey")])
    )
    assert reg.last_fallback_provider == "second"
    assert "hey" in result


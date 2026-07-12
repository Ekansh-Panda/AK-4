"""Provider registry, availability reporting and active-provider selection.

The registry holds every known provider (mock + real). The *active* provider is
the one chat uses; it is persisted via SettingsService and falls back to "mock"
whenever the selected provider has no API key configured, so chat always works.
"""

from __future__ import annotations

import time
from collections.abc import AsyncIterator, Iterable
from dataclasses import dataclass

from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.logging import get_logger
from app.services.providers.base import ModelProvider
from app.services.providers.cloudflare import CloudflareProvider
from app.services.providers.cohere import CohereProvider
from app.services.providers.gemini import GeminiProvider
from app.services.providers.huggingface import HuggingFaceProvider
from app.services.providers.mock_provider import MockProvider
from app.services.providers.openai_compatible import OpenAICompatibleProvider
from app.services.providers.openai_family import (
    GroqProvider,
    MistralProvider,
    OpenRouterProvider,
    SambaNovaProvider,
)
from app.services.settings_service import ACTIVE_PROVIDER_KEY, SettingsService

logger = get_logger(__name__)

MOCK = "mock"

# Exponential backoff (seconds) between 429/retryable attempts before falling
# back to the next provider in the pool.
_RETRY_DELAYS = [1, 2, 4]


@dataclass
class ProviderAvailability:
    name: str
    configured: bool
    available: bool


class ProviderRegistry:
    def __init__(self) -> None:
        self._providers: dict[str, ModelProvider] = {}
        self._default: str | None = None
        # In-memory active selection; hydrated from settings via load_active().
        self._active: str | None = None
        self._ping_cache: dict[str, tuple[float, bool]] = {}
        self._ping_cache_ttl: float = 60.0

    def register(self, provider: ModelProvider, *, default: bool = False) -> None:
        self._providers[provider.name] = provider
        if default or self._default is None:
            self._default = provider.name

    # --- lookup ---
    def get(self, name: str | None = None) -> ModelProvider:
        """Resolve a provider, falling back to mock when unavailable.

        With no explicit ``name`` this returns the active provider if it is
        available, otherwise the mock provider.
        """
        if name:
            if name not in self._providers:
                raise KeyError(f"No provider registered for '{name}'")
            return self._providers[name]
        chosen = self._active or self._default or MOCK
        provider = self._providers.get(chosen)
        if provider is not None and provider.available():
            return provider
        # Fall back to mock so chat never breaks.
        return self._providers.get(MOCK) or next(iter(self._providers.values()))

    def list(self) -> list[ModelProvider]:
        return list(self._providers.values())

    def has(self, name: str) -> bool:
        return name in self._providers

    @property
    def default_name(self) -> str | None:
        return self._default

    # --- active provider ---
    @property
    def active_name(self) -> str:
        return self._active or self._default or MOCK

    def set_active(self, name: str) -> str:
        if name not in self._providers:
            raise KeyError(f"No provider registered for '{name}'")
        self._active = name
        return name

    def load_active(self, db: Session) -> str:
        """Hydrate the active selection from persisted settings.

        Falls back to ``settings.DEFAULT_PROVIDER`` then "mock". Stored as-is even
        if the provider lacks a key — get() handles the runtime fallback.
        """
        stored = SettingsService(db).get(ACTIVE_PROVIDER_KEY)
        chosen = stored or settings.DEFAULT_PROVIDER or MOCK
        if chosen not in self._providers:
            chosen = MOCK
        self._active = chosen
        return chosen

    def persist_active(self, db: Session, name: str) -> str:
        """Set + persist the active provider via SettingsService."""
        self.set_active(name)
        SettingsService(db).set(ACTIVE_PROVIDER_KEY, name)
        return name

    # --- availability ---
    def availability(self) -> list[ProviderAvailability]:
        out: list[ProviderAvailability] = []
        for p in self._providers.values():
            avail = p.available()
            out.append(
                ProviderAvailability(name=p.name, configured=avail, available=avail)
            )
        return out

    async def ping_all(self) -> dict[str, bool]:
        """Ping every configured provider concurrently. Returns {name: reachable}."""
        import asyncio

        configured = [(n, p) for n, p in self._providers.items() if p.available()]
        if not configured:
            return {}
        names = [n for n, _ in configured]
        tasks = [p.ping() for _, p in configured]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        return {
            name: (result is True)
            for name, result in zip(names, results)
        }

    def _read_ping_cache(self) -> dict[str, bool]:
        now = time.monotonic()
        return {
            name: reachable
            for name, (ts, reachable) in self._ping_cache.items()
            if (now - ts) < self._ping_cache_ttl
        }

    async def ping_with_cache(self, *, force_refresh: bool = False) -> dict[str, bool]:
        """Best-effort reachability check with in-memory caching.

        Returns cached results when fresh (<60 s old); otherwise refreshes
        stale entries by live-pinging and stores the outcome. Never raises.
        """
        if force_refresh:
            self._ping_cache.clear()

        now = time.monotonic()
        configured = {n: p for n, p in self._providers.items() if p.available()}
        if not configured:
            return {}

        cached: dict[str, bool] = {}
        stale: list[str] = []
        for name, p in configured.items():
            entry = self._ping_cache.get(name)
            if entry is not None and (now - entry[0]) < self._ping_cache_ttl:
                cached[name] = entry[1]
            else:
                stale.append(name)

        if stale:
            try:
                live = await self.ping_all()
            except Exception:
                live = {}
            for name in stale:
                if name in live:
                    reachable = live[name]
                elif name in self._ping_cache:
                    reachable = self._ping_cache[name][1]
                else:
                    reachable = configured[name].available()
                self._ping_cache[name] = (now, reachable)
                cached[name] = reachable

        return cached

    # --- resilience: 429-aware fallback chain ---
    def _fallback_order(self, *, exclude: str | None = None) -> list[ModelProvider]:
        """Ordered providers for fallback.

        Prefers real providers that are ``available()`` (key configured), in
        registration order, then appends the always-available mock provider last.
        ``exclude`` skips a provider already tried as the primary.
        """
        order: list[ModelProvider] = []
        for name, p in self._providers.items():
            if name == MOCK:
                continue
            if exclude is not None and name == exclude:
                continue
            if p.available():
                order.append(p)
        mock = self._providers.get(MOCK)
        if mock is not None:
            order.append(mock)
        return order

    @property
    def last_fallback_provider(self) -> str | None:
        """Name of the provider that actually served the last fallback chat."""
        return getattr(self, "_last_fallback", None)

    async def chat_with_fallback(
        self,
        messages: Iterable,
        *,
        model: str | None = None,
        system_prompt: str | None = None,
        tools: list[dict] | None = None,
        max_retries: int = 3,
    ) -> str | object:
        """429-aware chat with silent provider fallback, mock as last resort.

        Tries the active provider (with retry/backoff). On persistent failure or
        a non-retryable error it silently moves to the next available provider in
        the pool, and finally the mock provider — the user is never left without
        a reply.
        """
        primary = self.get()
        chain = [primary] + self._fallback_order(exclude=primary.name)
        for provider in chain:
            try:
                logger.info("chat attempt via provider %s", provider.name)
                result = await provider.chat_with_retry(
                    messages,
                    model=model,
                    system_prompt=system_prompt,
                    tools=tools,
                    max_retries=max_retries,
                )
                self._last_fallback = provider.name
                return result
            except Exception as exc:  # noqa: BLE001 - try the next provider
                logger.warning(
                    "Provider %s failed, falling back to next: %s",
                    provider.name,
                    exc,
                )
                continue
        # Mock is always last in the chain and never raises; this is a safety net.
        mock = self._providers.get(MOCK)
        if mock is None:
            raise RuntimeError("No provider (including mock) available for chat")
        logger.error("All providers failed; using mock as final fallback")
        self._last_fallback = MOCK
        return await mock.chat(
            messages, model=model, system_prompt=system_prompt, tools=tools
        )

    async def stream_with_fallback(
        self,
        messages: Iterable,
        *,
        model: str | None = None,
        system_prompt: str | None = None,
        tools: list[dict] | None = None,
        max_retries: int = 3,
    ) -> AsyncIterator:
        """Streaming variant of :meth:`chat_with_fallback`.

        Walks the same provider chain, yielding tokens from the first provider
        that streams successfully. The mock provider is the guaranteed last
        resort.
        """
        primary = self.get()
        chain = [primary] + self._fallback_order(exclude=primary.name)
        last_exc: Exception | None = None
        for provider in chain:
            try:
                async for chunk in provider.stream_with_retry(
                    messages,
                    model=model,
                    system_prompt=system_prompt,
                    tools=tools,
                    max_retries=max_retries,
                ):
                    yield chunk
                self._last_fallback = provider.name
                return
            except Exception as exc:  # noqa: BLE001 - try the next provider
                last_exc = exc
                logger.warning(
                    "Provider %s stream failed, falling back to next: %s",
                    provider.name,
                    exc,
                )
                continue
        mock = self._providers.get(MOCK)
        if mock is None:
            raise RuntimeError("No provider (including mock) available for stream")
        logger.error("All providers failed; using mock stream as final fallback")
        self._last_fallback = MOCK
        async for chunk in mock.stream(
            messages, model=model, system_prompt=system_prompt, tools=tools
        ):
            yield chunk


# Process-wide registry: mock (always available) + real providers (gated on keys).
registry = ProviderRegistry()
registry.register(MockProvider(), default=True)
registry.register(OpenAICompatibleProvider())
registry.register(GeminiProvider())
registry.register(GroqProvider())
registry.register(MistralProvider())
registry.register(SambaNovaProvider())
registry.register(OpenRouterProvider())
registry.register(HuggingFaceProvider())
registry.register(CohereProvider())
registry.register(CloudflareProvider())

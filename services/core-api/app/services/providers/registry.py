"""Provider registry, availability reporting and active-provider selection.

The registry holds every known provider (mock + real). The *active* provider is
the one chat uses; it is persisted via SettingsService and falls back to "mock"
whenever the selected provider has no API key configured, so chat always works.
"""

from __future__ import annotations

import time
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

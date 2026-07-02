"""Model provider abstraction.

A provider talks to an LLM backend. The mock provider lets chat work fully
offline. Real providers plug in behind the same interface.

TODO(Odysseus): wire real providers (local + hosted LLMs) and a router that
picks a model per persona mode / task.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import AsyncIterator, Iterable
from dataclasses import dataclass


@dataclass
class ChatMessage:
    role: str  # "system" | "user" | "assistant" | "tool"
    content: str | None = None
    tool_calls: list[dict] | None = None
    tool_call_id: str | None = None


@dataclass
class ModelDescriptor:
    id: str
    name: str
    provider: str
    context_window: int | None = None


class ModelProvider(ABC):
    """Interface every model backend must implement."""

    name: str = "base"

    def available(self) -> bool:
        """Whether this provider is usable right now (e.g. API key present).

        Defaults to True so offline providers (mock) are always available. Real
        providers override this to report missing credentials without crashing.
        """
        return True

    async def ping(self) -> bool:
        """Best-effort reachability check.
        
        Real providers can override this to do a cheap HTTP GET to their base URL
        and return False on connection errors. Defaults to True if available().
        """
        return self.available()

    @abstractmethod
    def list_models(self) -> list[ModelDescriptor]:
        """Return the models this provider exposes."""

    @abstractmethod
    async def chat(
        self,
        messages: Iterable[ChatMessage],
        *,
        model: str | None = None,
        system_prompt: str | None = None,
        tools: list[dict] | None = None,
    ) -> str | ChatMessage:
        """Return a single completion string or a ChatMessage with tool calls."""

    @abstractmethod
    async def stream(
        self,
        messages: Iterable[ChatMessage],
        *,
        model: str | None = None,
        system_prompt: str | None = None,
        tools: list[dict] | None = None,
    ) -> AsyncIterator[str | ChatMessage]:
        """Yield completion tokens/chunks. If tool calls are requested, yield a ChatMessage."""

    async def embed(self, texts: list[str]) -> list[list[float]]:
        """Return embeddings for ``texts``. Optional capability.

        Defaults to NotImplementedError so callers can probe and fall back (e.g.
        to a local sentence-transformers model) without crashing.
        """
        raise NotImplementedError(f"{self.name} provider does not support embeddings")

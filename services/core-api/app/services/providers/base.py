"""Model provider abstraction.

A provider talks to an LLM backend. The mock provider lets chat work fully
offline. Real providers plug in behind the same interface.

TODO(Odysseus): wire real providers (local + hosted LLMs) and a router that
picks a model per persona mode / task.
"""

from __future__ import annotations

import asyncio
from abc import ABC, abstractmethod
from collections.abc import AsyncIterator, Iterable
from dataclasses import dataclass

from app.core.logging import get_logger

logger = get_logger(__name__)

# Exponential backoff (seconds) between retryable attempts: 1s, 2s, 4s.
_RETRY_BACKOFF = (1, 2, 4)


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

    # --- resilience: 429-aware retry + stream retry ---
    def _extract_status_code(self, error: Exception) -> int | None:
        """Pull an HTTP status code off a provider error if present.

        Handles httpx.HTTPStatusError (``.response.status_code``) and providers
        that raise with a ``.status_code`` attribute directly.
        """
        resp = getattr(error, "response", None)
        if resp is not None:
            code = getattr(resp, "status_code", None)
            if isinstance(code, int):
                return code
        code = getattr(error, "status_code", None)
        if isinstance(code, int):
            return code
        return None

    def _is_retryable(self, error: Exception) -> bool:
        """Whether a failed call should be retried before fallback.

        Retry on: rate-limit (429), request timeout (408), 5xx, and any
        transport/network/timeout error (no HTTP status). Do NOT retry on
        auth (401/403) or bad request (400) — those will never succeed.
        """
        status = self._extract_status_code(error)
        if status is not None:
            if status in (429, 408):
                return True
            if 500 <= status < 600:
                return True
            return False
        # No status -> treat as transient transport/network/timeout failure.
        try:
            import httpx

            if isinstance(error, (httpx.TimeoutException, httpx.TransportError)):
                return True
        except ImportError:
            pass
        if isinstance(error, (TimeoutError, ConnectionError, OSError)):
            return True
        return False

    def _extract_retry_after(self, error: Exception) -> float | None:
        """Parse a ``Retry-After`` delay (seconds) from a 429 error.

        Reads the ``Retry-After`` header off ``error.response`` (httpx-style),
        falling back to an ``error.retry_after`` attribute some providers set
        directly. Returns ``None`` when unavailable.
        """
        retry_after: float | None = None
        resp = getattr(error, "response", None)
        if resp is not None:
            headers = getattr(resp, "headers", None)
            if headers is not None:
                raw = headers.get("Retry-After") if hasattr(headers, "get") else None
                if raw is not None:
                    try:
                        retry_after = float(raw)
                    except (TypeError, ValueError):
                        # HTTP-date Retry-After: honor with a short fixed delay.
                        retry_after = 1.0
        if retry_after is None and hasattr(error, "retry_after"):
            try:
                retry_after = float(error.retry_after)  # type: ignore[attr-defined]
            except (TypeError, ValueError):
                retry_after = None
        return retry_after

    def _retry_delay(self, attempt: int, error: Exception) -> float:
        """Backoff delay (seconds) before retry ``attempt`` (0-indexed)."""
        explicit = self._extract_retry_after(error)
        if explicit is not None:
            return min(max(explicit, 0.0), 30.0)
        if attempt < len(_RETRY_BACKOFF):
            return float(_RETRY_BACKOFF[attempt])
        return float(_RETRY_BACKOFF[-1] * 2 ** (attempt - len(_RETRY_BACKOFF) + 1))

    async def chat_with_retry(
        self,
        messages: Iterable[ChatMessage],
        *,
        model: str | None = None,
        system_prompt: str | None = None,
        tools: list[dict] | None = None,
        max_retries: int = 3,
    ) -> str | ChatMessage:
        """Call ``chat()`` with 429-aware exponential backoff.

        Retries on rate-limit (429), timeout and connection errors. Non-retryable
        errors (auth, bad request) are re-raised immediately so the caller's
        fallback chain can take over. Exhausted retries re-raise the last error.
        """
        attempts = max(1, max_retries)
        last_exc: Exception | None = None
        for attempt in range(attempts):
            try:
                return await self.chat(
                    messages, model=model, system_prompt=system_prompt, tools=tools
                )
            except Exception as exc:  # noqa: BLE001 - classify before re-raise
                last_exc = exc
                if not self._is_retryable(exc):
                    logger.warning(
                        "Provider %s non-retryable error, not backing off: %s",
                        self.name,
                        exc,
                    )
                    raise
                delay = self._retry_delay(attempt, exc)
                logger.warning(
                    "Provider %s rate-limited/error (attempt %d/%d), "
                    "retrying in %.1fs: %s",
                    self.name,
                    attempt + 1,
                    attempts,
                    delay,
                    exc,
                )
                await asyncio.sleep(delay)
        assert last_exc is not None
        raise last_exc

    async def stream_with_retry(
        self,
        messages: Iterable[ChatMessage],
        *,
        model: str | None = None,
        system_prompt: str | None = None,
        tools: list[dict] | None = None,
        max_retries: int = 3,
    ) -> AsyncIterator[str | ChatMessage]:
        """Stream with 429-aware retry.

        Retries the whole stream while no token has been yielded yet. Once output
        has started we cannot rewind a live stream, so a mid-stream failure is
        re-raised for the caller to handle (e.g. degrade to mock).
        """
        attempts = max(1, max_retries)
        last_exc: Exception | None = None
        for attempt in range(attempts):
            yielded = False
            try:
                async for chunk in self.stream(
                    messages, model=model, system_prompt=system_prompt, tools=tools
                ):
                    yielded = True
                    yield chunk
                return
            except Exception as exc:  # noqa: BLE001
                last_exc = exc
                if yielded:
                    logger.warning(
                        "Provider %s stream error after tokens (attempt %d), "
                        "not retrying: %s",
                        self.name,
                        attempt + 1,
                        exc,
                    )
                    raise
                if not self._is_retryable(exc):
                    logger.warning(
                        "Provider %s non-retryable stream error: %s",
                        self.name,
                        exc,
                    )
                    raise
                delay = self._retry_delay(attempt, exc)
                logger.warning(
                    "Provider %s stream error (attempt %d/%d), "
                    "retrying in %.1fs: %s",
                    self.name,
                    attempt + 1,
                    attempts,
                    delay,
                    exc,
                )
                await asyncio.sleep(delay)
        assert last_exc is not None
        raise last_exc

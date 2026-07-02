"""Cohere provider (Chat API v2).

Uses ``cohere.AsyncClientV2`` (lazily imported). Maps Cohere's content blocks
and streaming events to the common ``str`` / ``AsyncIterator[str]`` interface.
Unavailable without ``COHERE_API_KEY``; SDK never imported at module load.
"""

from __future__ import annotations

from collections.abc import AsyncIterator, Iterable

from app.core.config import settings
from app.core.logging import get_logger
from app.services.providers.base import ChatMessage, ModelDescriptor, ModelProvider

logger = get_logger(__name__)


class CohereProvider(ModelProvider):
    name = "cohere"

    def __init__(self) -> None:
        self._api_key = settings.COHERE_API_KEY
        self._model = settings.COHERE_MODEL

    def available(self) -> bool:
        return bool(self._api_key)

    async def ping(self) -> bool:
        if not self.available():
            return False
        import httpx
        try:
            async with httpx.AsyncClient(timeout=3.0) as client:
                resp = await client.get(
                    "https://api.cohere.com/v1/models",
                    headers={"Authorization": f"Bearer {self._api_key}"},
                )
                return True
        except Exception:
            return False

    def list_models(self) -> list[ModelDescriptor]:
        return [ModelDescriptor(id=self._model, name=self._model, provider=self.name)]

    def _wire(
        self, messages: Iterable[ChatMessage], system_prompt: str | None
    ) -> list[dict[str, str]]:
        wire: list[dict[str, str]] = []
        if system_prompt:
            wire.append({"role": "system", "content": system_prompt})
        for m in messages:
            role = m.role if m.role in ("system", "user", "assistant") else "user"
            wire.append({"role": role, "content": m.content or ""})
        return wire

    def _client(self):
        import cohere  # lazy

        return cohere.AsyncClientV2(api_key=self._api_key)

    @staticmethod
    def _text_from_message(message) -> str:
        # v2 returns message.content as a list of blocks with .text
        content = getattr(message, "content", None)
        if isinstance(content, list):
            return "".join(getattr(b, "text", "") for b in content)
        return content or ""

    async def chat(
        self,
        messages: Iterable[ChatMessage],
        *,
        model: str | None = None,
        system_prompt: str | None = None,
        tools: list[dict] | None = None,
    ) -> str:
        if not self.available():
            raise RuntimeError("Cohere provider unavailable: missing COHERE_API_KEY")
        client = self._client()
        resp = await client.chat(
            model=model or self._model,
            messages=self._wire(messages, system_prompt),
        )
        return self._text_from_message(resp.message)

    async def stream(
        self,
        messages: Iterable[ChatMessage],
        *,
        model: str | None = None,
        system_prompt: str | None = None,
        tools: list[dict] | None = None,
    ) -> AsyncIterator[str]:
        if not self.available():
            raise RuntimeError("Cohere provider unavailable: missing COHERE_API_KEY")
        client = self._client()
        stream = client.chat_stream(
            model=model or self._model,
            messages=self._wire(messages, system_prompt),
        )
        async for event in stream:
            if getattr(event, "type", None) == "content-delta":
                try:
                    token = event.delta.message.content.text
                except AttributeError:
                    token = None
                if token:
                    yield token

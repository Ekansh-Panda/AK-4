"""Cloudflare Workers AI provider (REST).

POSTs to ``/accounts/{account_id}/ai/run/{model}`` with an OpenAI-style
``messages`` array. ``httpx`` is imported lazily. Requires both
``CLOUDFLARE_API_KEY`` and ``CLOUDFLARE_ACCOUNT_ID``; otherwise unavailable.
"""

from __future__ import annotations

import json
from collections.abc import AsyncIterator, Iterable

from app.core.config import settings
from app.core.logging import get_logger
from app.services.providers.base import ChatMessage, ModelDescriptor, ModelProvider

logger = get_logger(__name__)

_BASE = "https://api.cloudflare.com/client/v4"


class CloudflareProvider(ModelProvider):
    name = "cloudflare"

    def __init__(self) -> None:
        self._api_key = settings.CLOUDFLARE_API_KEY
        self._account_id = settings.CLOUDFLARE_ACCOUNT_ID
        self._model = settings.CLOUDFLARE_MODEL

    def available(self) -> bool:
        return bool(self._api_key and self._account_id)

    async def ping(self) -> bool:
        if not self.available():
            return False
        import httpx
        try:
            async with httpx.AsyncClient(timeout=3.0) as client:
                resp = await client.get(
                    f"{_BASE}/accounts/{self._account_id}/ai/models/search",
                    headers=self._headers(),
                )
                return True
        except Exception:
            return False

    def list_models(self) -> list[ModelDescriptor]:
        return [ModelDescriptor(id=self._model, name=self._model, provider=self.name)]

    def _url(self, model: str | None) -> str:
        return f"{_BASE}/accounts/{self._account_id}/ai/run/{model or self._model}"

    def _headers(self) -> dict[str, str]:
        return {"Authorization": f"Bearer {self._api_key}", "Content-Type": "application/json"}

    def _messages(
        self, messages: Iterable[ChatMessage], system_prompt: str | None
    ) -> list[dict[str, str]]:
        wire: list[dict[str, str]] = []
        if system_prompt:
            wire.append({"role": "system", "content": system_prompt})
        for m in messages:
            role = m.role if m.role in ("system", "user", "assistant") else "user"
            wire.append({"role": role, "content": m.content or ""})
        return wire

    async def chat(
        self,
        messages: Iterable[ChatMessage],
        *,
        model: str | None = None,
        system_prompt: str | None = None,
        tools: list[dict] | None = None,
    ) -> str:
        if not self.available():
            raise RuntimeError("Cloudflare provider unavailable: missing key/account")
        import httpx  # lazy

        async with httpx.AsyncClient(timeout=60.0) as client:
            resp = await client.post(
                self._url(model),
                headers=self._headers(),
                json={"messages": self._messages(messages, system_prompt)},
            )
            resp.raise_for_status()
            data = resp.json()
        return (data.get("result") or {}).get("response", "") or ""

    async def stream(
        self,
        messages: Iterable[ChatMessage],
        *,
        model: str | None = None,
        system_prompt: str | None = None,
        tools: list[dict] | None = None,
    ) -> AsyncIterator[str]:
        if not self.available():
            raise RuntimeError("Cloudflare provider unavailable: missing key/account")
        import httpx  # lazy

        async with httpx.AsyncClient(timeout=120.0) as client:
            async with client.stream(
                "POST",
                self._url(model),
                headers=self._headers(),
                json={"messages": self._messages(messages, system_prompt), "stream": True},
            ) as resp:
                resp.raise_for_status()
                async for line in resp.aiter_lines():
                    if not line or not line.startswith("data:"):
                        continue
                    chunk = line[len("data:"):].strip()
                    if chunk == "[DONE]":
                        break
                    try:
                        token = json.loads(chunk).get("response")
                    except json.JSONDecodeError:
                        continue
                    if token:
                        yield token

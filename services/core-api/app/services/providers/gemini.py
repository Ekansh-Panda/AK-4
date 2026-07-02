"""Google Gemini provider (REST via httpx).

Uses the Generative Language API ``generateContent`` /
``streamGenerateContent`` endpoints. ``httpx`` is imported lazily so the module
imports cleanly in lite-mode. Reports ``available() is False`` when no key is
configured rather than crashing.

Key resolution: ``GEMINI_API_KEY`` preferred, ``GOOGLE_API_KEY`` accepted as an
alias (see ``settings.gemini_key``).
"""

from __future__ import annotations

import json
from collections.abc import AsyncIterator, Iterable

from app.core.config import settings
from app.core.logging import get_logger
from app.services.providers.base import ChatMessage, ModelDescriptor, ModelProvider

logger = get_logger(__name__)

_BASE = "https://generativelanguage.googleapis.com/v1beta"


class GeminiProvider(ModelProvider):
    name = "gemini"

    def __init__(self, *, api_key: str | None = None, model: str | None = None) -> None:
        self._api_key = api_key if api_key is not None else settings.gemini_key
        self._model = model or settings.GEMINI_MODEL

    def available(self) -> bool:
        return bool(self._api_key)

    async def ping(self) -> bool:
        if not self.available():
            return False
        import httpx
        try:
            async with httpx.AsyncClient(timeout=3.0) as client:
                resp = await client.get(
                    f"{_BASE}/models", params={"key": self._api_key}
                )
                return True
        except Exception:
            return False

    def list_models(self) -> list[ModelDescriptor]:
        return [
            ModelDescriptor(
                id=self._model,
                name=self._model,
                provider=self.name,
                context_window=None,
            )
        ]

    # --- payload mapping ---
    def _payload(
        self, messages: Iterable[ChatMessage], *, system_prompt: str | None
    ) -> dict:
        contents: list[dict] = []
        for m in messages:
            # Gemini roles: "user" | "model". Map assistant -> model; system
            # text is folded into systemInstruction below.
            if m.role == "system":
                continue
            role = "model" if m.role == "assistant" else "user"
            contents.append({"role": role, "parts": [{"text": m.content or ""}]})
        payload: dict = {"contents": contents}
        if system_prompt:
            payload["systemInstruction"] = {"parts": [{"text": system_prompt}]}
        return payload

    @staticmethod
    def _extract_text(obj: dict) -> str:
        try:
            parts = obj["candidates"][0]["content"]["parts"]
            return "".join(p.get("text", "") for p in parts)
        except (KeyError, IndexError, TypeError):
            return ""

    # --- inference ---
    async def chat(
        self,
        messages: Iterable[ChatMessage],
        *,
        model: str | None = None,
        system_prompt: str | None = None,
        tools: list[dict] | None = None,
    ) -> str:
        if not self.available():
            raise RuntimeError("Gemini provider unavailable: missing GEMINI_API_KEY")
        import httpx  # lazy

        mdl = model or self._model
        url = f"{_BASE}/models/{mdl}:generateContent"
        async with httpx.AsyncClient(timeout=60.0) as client:
            resp = await client.post(
                url,
                params={"key": self._api_key},
                json=self._payload(messages, system_prompt=system_prompt),
            )
            resp.raise_for_status()
            data = resp.json()
        return self._extract_text(data)

    async def stream(
        self,
        messages: Iterable[ChatMessage],
        *,
        model: str | None = None,
        system_prompt: str | None = None,
        tools: list[dict] | None = None,
    ) -> AsyncIterator[str]:
        if not self.available():
            raise RuntimeError("Gemini provider unavailable: missing GEMINI_API_KEY")
        import httpx  # lazy

        mdl = model or self._model
        url = f"{_BASE}/models/{mdl}:streamGenerateContent"
        async with httpx.AsyncClient(timeout=120.0) as client:
            async with client.stream(
                "POST",
                url,
                params={"key": self._api_key, "alt": "sse"},
                json=self._payload(messages, system_prompt=system_prompt),
            ) as resp:
                resp.raise_for_status()
                async for line in resp.aiter_lines():
                    if not line or not line.startswith("data:"):
                        continue
                    chunk = line[len("data:") :].strip()
                    if not chunk:
                        continue
                    try:
                        token = self._extract_text(json.loads(chunk))
                    except json.JSONDecodeError:
                        continue
                    if token:
                        yield token

    chat_stream = stream

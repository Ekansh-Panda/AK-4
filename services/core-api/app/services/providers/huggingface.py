"""Hugging Face Inference provider.

Uses ``huggingface_hub.AsyncInferenceClient`` (lazily imported) which speaks the
OpenAI-style ``chat_completion`` API against HF-hosted models. Reports
unavailable when no token is set; never imports the SDK at module load.
"""

from __future__ import annotations

from collections.abc import AsyncIterator, Iterable

from app.core.config import settings
from app.core.logging import get_logger
from app.services.providers.base import ChatMessage, ModelDescriptor, ModelProvider

logger = get_logger(__name__)


class HuggingFaceProvider(ModelProvider):
    name = "huggingface"

    def __init__(self) -> None:
        self._api_key = settings.HUGGINGFACE_API_KEY
        self._model = settings.HUGGINGFACE_MODEL

    def available(self) -> bool:
        return bool(self._api_key)

    async def ping(self) -> bool:
        if not self.available():
            return False
        import httpx
        try:
            async with httpx.AsyncClient(timeout=3.0) as client:
                resp = await client.get(
                    "https://huggingface.co/api/whoami-v2",
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
        from huggingface_hub import AsyncInferenceClient  # lazy

        return AsyncInferenceClient(token=self._api_key)

    async def chat(
        self,
        messages: Iterable[ChatMessage],
        *,
        model: str | None = None,
        system_prompt: str | None = None,
        tools: list[dict] | None = None,
    ) -> str:
        if not self.available():
            raise RuntimeError("HuggingFace provider unavailable: missing token")
        client = self._client()
        resp = await client.chat_completion(
            messages=self._wire(messages, system_prompt),
            model=model or self._model,
            max_tokens=1024,
        )
        return resp.choices[0].message.content or ""

    async def stream(
        self,
        messages: Iterable[ChatMessage],
        *,
        model: str | None = None,
        system_prompt: str | None = None,
        tools: list[dict] | None = None,
    ) -> AsyncIterator[str]:
        if not self.available():
            raise RuntimeError("HuggingFace provider unavailable: missing token")
        client = self._client()
        stream = await client.chat_completion(
            messages=self._wire(messages, system_prompt),
            model=model or self._model,
            max_tokens=1024,
            stream=True,
        )
        async for event in stream:
            try:
                token = event.choices[0].delta.content
            except (AttributeError, IndexError):
                token = None
            if token:
                yield token

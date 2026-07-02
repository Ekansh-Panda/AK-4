"""OpenAI-compatible providers: Groq, Mistral, SambaNova, OpenRouter.

Each is the OpenAI Chat Completions wire format at a different base URL with a
different API key, so they subclass ``OpenAICompatibleProvider`` and only swap
``name`` + endpoint + credentials. ``httpx`` stays lazily imported in the base.
Unconfigured providers report ``available() is False`` and the registry falls
back to mock — nothing crashes when a key is missing.
"""

from __future__ import annotations

from app.core.config import settings
from app.services.providers.openai_compatible import OpenAICompatibleProvider


class GroqProvider(OpenAICompatibleProvider):
    name = "groq"

    def __init__(self) -> None:
        super().__init__(
            api_key=settings.GROQ_API_KEY,
            base_url="https://api.groq.com/openai/v1",
            model=settings.GROQ_MODEL,
        )


class MistralProvider(OpenAICompatibleProvider):
    name = "mistral"

    def __init__(self) -> None:
        super().__init__(
            api_key=settings.MISTRAL_API_KEY,
            base_url="https://api.mistral.ai/v1",
            model=settings.MISTRAL_MODEL,
        )


class SambaNovaProvider(OpenAICompatibleProvider):
    name = "sambanova"

    def __init__(self) -> None:
        super().__init__(
            api_key=settings.SAMBANOVA_API_KEY,
            base_url="https://api.sambanova.ai/v1",
            model=settings.SAMBANOVA_MODEL,
        )


class OpenRouterProvider(OpenAICompatibleProvider):
    name = "openrouter"

    def __init__(self) -> None:
        super().__init__(
            api_key=settings.OPENROUTER_API_KEY,
            base_url="https://openrouter.ai/api/v1",
            model=settings.OPENROUTER_MODEL,
        )

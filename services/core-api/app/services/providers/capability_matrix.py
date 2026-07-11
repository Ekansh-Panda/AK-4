"""Capability matrix for orchestrator provider selection and /providers listing.

Single source of truth for model metadata. After Option A, the adapters are
demoted to UI-only; this matrix drives both LiteLLM deployment construction and
the /providers endpoint so listing cannot drift from routing.
"""

from __future__ import annotations

from app.core.config import settings
from app.services.providers.base import ModelDescriptor


_MATRIX: dict[str, dict[str, dict]] = {
    "openai": {
        "gpt-4o-mini": {
            "context_window": 128000,
            "tools": True,
            "quality_tier": "standard",
            "persona_ok": True,
        },
        "gpt-4o": {
            "context_window": 128000,
            "tools": True,
            "quality_tier": "premium",
            "persona_ok": True,
        },
        "o3-mini": {
            "context_window": 200000,
            "tools": True,
            "quality_tier": "premium",
            "persona_ok": True,
        },
    },
    "gemini": {
        "gemini-1.5-flash": {
            "context_window": 1048000,
            "tools": True,
            "quality_tier": "standard",
            "persona_ok": True,
        },
        "gemini-1.5-pro": {
            "context_window": 2150000,
            "tools": True,
            "quality_tier": "premium",
            "persona_ok": True,
        },
        "gemini-2.0-flash": {
            "context_window": 1000000,
            "tools": True,
            "quality_tier": "standard",
            "persona_ok": True,
        },
    },
    "groq": {
        "llama-3.3-70b-versatile": {
            "context_window": 128000,
            "tools": True,
            "quality_tier": "standard",
            "persona_ok": True,
        },
        "llama-3.1-8b-instant": {
            "context_window": 128000,
            "tools": True,
            "quality_tier": "standard",
            "persona_ok": True,
        },
    },
    "mistral": {
        "mistral-small-latest": {
            "context_window": 32000,
            "tools": True,
            "quality_tier": "standard",
            "persona_ok": True,
        },
        "mistral-large-latest": {
            "context_window": 32000,
            "tools": True,
            "quality_tier": "premium",
            "persona_ok": True,
        },
    },
    "sambanova": {
        "Meta-Llama-3.1-8B-Instruct": {
            "context_window": 4096,
            "tools": False,
            "quality_tier": "standard",
            "persona_ok": True,
        },
    },
    "openrouter": {
        "openai/gpt-4o-mini": {
            "context_window": 128000,
            "tools": True,
            "quality_tier": "standard",
            "persona_ok": True,
        },
        "openai/gpt-4o": {
            "context_window": 128000,
            "tools": True,
            "quality_tier": "premium",
            "persona_ok": True,
        },
        "google/gemini-2.0-flash-001": {
            "context_window": 1000000,
            "tools": True,
            "quality_tier": "standard",
            "persona_ok": True,
        },
        "meta-llama/llama-3.1-8b-instruct": {
            "context_window": 128000,
            "tools": True,
            "quality_tier": "standard",
            "persona_ok": True,
        },
    },
    "huggingface": {
        "meta-llama/Llama-3.1-8B-Instruct": {
            "context_window": 8192,
            "tools": False,
            "quality_tier": "standard",
            "persona_ok": True,
        },
    },
    "cohere": {
        "command-r": {
            "context_window": 128000,
            "tools": True,
            "quality_tier": "standard",
            "persona_ok": True,
        },
    },
    "cloudflare": {
        "@cf/meta/llama-3.1-8b-instruct": {
            "context_window": 8192,
            "tools": False,
            "quality_tier": "standard",
            "persona_ok": True,
        },
    },
    "mock": {
        "mock-echo": {
            "context_window": 8192,
            "tools": True,
            "quality_tier": "standard",
            "persona_ok": True,
        },
    },
}


def _default_model_map() -> dict[str, str]:
    return {
        "openai": settings.OPENAI_MODEL,
        "gemini": settings.GEMINI_MODEL,
        "groq": settings.GROQ_MODEL,
        "mistral": settings.MISTRAL_MODEL,
        "sambanova": settings.SAMBANOVA_MODEL,
        "openrouter": settings.OPENROUTER_MODEL,
        "huggingface": settings.HUGGINGFACE_MODEL,
        "cohere": settings.COHERE_MODEL,
        "cloudflare": settings.CLOUDFLARE_MODEL,
        "mock": "mock-echo",
    }


def list_models(provider_name: str) -> list[ModelDescriptor]:
    caps = _MATRIX.get(provider_name, {})
    return [
        ModelDescriptor(
            id=model_id,
            name=model_id,
            provider=provider_name,
            context_window=meta.get("context_window"),
        )
        for model_id, meta in caps.items()
    ]


def list_all_models() -> list[ModelDescriptor]:
    out: list[ModelDescriptor] = []
    for provider_name, caps in _MATRIX.items():
        for model_id, meta in caps.items():
            out.append(
                ModelDescriptor(
                    id=model_id,
                    name=model_id,
                    provider=provider_name,
                    context_window=meta.get("context_window"),
                )
            )
    return out


def get_default_model(provider_name: str) -> str:
    return _default_model_map().get(provider_name, "mock-echo")


def get_capability(provider_name: str, model_id: str) -> dict | None:
    return _MATRIX.get(provider_name, {}).get(model_id)

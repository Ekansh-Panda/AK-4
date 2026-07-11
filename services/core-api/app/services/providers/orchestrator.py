"""LiteLLM-based orchestrating provider.

Wraps ``litellm.Router`` and exposes the same ``chat``/``stream`` interface as
``ModelProvider`` so ``ChatService`` can swap it in transparently.
"""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator, Iterable
from typing import Any

from app.core.config import settings
from app.core.logging import get_logger
from app.services.providers.base import (
    ChatMessage,
    ModelDescriptor,
    ModelProvider,
)
from app.services.providers.capability_matrix import (
    get_capability,
    get_default_model,
    list_all_models,
    list_models,
)
from app.services.providers.mock_provider import MockProvider
from app.services.providers.registry import ProviderRegistry

logger = get_logger(__name__)


class RouterBuildError(Exception):
    pass


class NoCandidateError(Exception):
    pass


def _build_litellm_deployments(keys_by_provider: dict[str, list[str]]) -> list[dict]:
    """Return LiteLLM ``Router`` deployment configs for configured providers."""
    provider_defaults = {
        "openai": {
            "model": settings.OPENAI_MODEL,
            "api_base": settings.OPENAI_BASE_URL,
        },
        "gemini": {
            "model": settings.GEMINI_MODEL,
        },
        "groq": {
            "model": settings.GROQ_MODEL,
            "api_base": "https://api.groq.com/openai/v1",
        },
        "mistral": {
            "model": settings.MISTRAL_MODEL,
            "api_base": "https://api.mistral.ai/v1",
        },
        "sambanova": {
            "model": settings.SAMBANOVA_MODEL,
            "api_base": "https://api.sambanova.ai/v1",
        },
        "openrouter": {
            "model": settings.OPENROUTER_MODEL,
            "api_base": "https://openrouter.ai/api/v1",
        },
        "huggingface": {
            "model": settings.HUGGINGFACE_MODEL,
        },
        "cohere": {
            "model": settings.COHERE_MODEL,
        },
        "cloudflare": {
            "model": settings.CLOUDFLARE_MODEL,
        },
    }
    deployments: list[dict] = []
    for provider_name, keys in keys_by_provider.items():
        if not keys:
            continue
        cfg = provider_defaults.get(provider_name, {})
        model = cfg.get("model") or get_default_model(provider_name)
        for idx, key in enumerate(keys):
            litellm_params: dict[str, Any] = {
                "model": model,
                "api_key": key,
            }
            if cfg.get("api_base"):
                litellm_params["api_base"] = cfg["api_base"]
            dep: dict[str, Any] = {
                "model_name": model,
                "litellm_params": litellm_params,
                "model_id": f"{provider_name}/{model}" if provider_name not in {"openai", "mock"} else model,
                "dimensions": {
                    "provider": provider_name,
                    "key_index": idx,
                },
            }
            if provider_name == "cloudflare" and settings.CLOUDFLARE_ACCOUNT_ID:
                dep["litellm_params"]["account_id"] = settings.CLOUDFLARE_ACCOUNT_ID
            deployments.append(dep)
    return deployments


class _Router:
    """Lazy wrapper around ``litellm.Router``."""

    def __init__(self, deployments: list[dict]) -> None:
        self._deployments = deployments
        self._router: Any = None
        self._init_lock = asyncio.Lock()

    async def _ensure(self) -> Any:
        if self._router is None:
            async with self._init_lock:
                if self._router is None:
                    try:
                        import litellm  # noqa: F401 - validate dep
                        from litellm import Router
                    except ImportError as exc:
                        raise RouterBuildError("litellm is not installed") from exc
                    if not self._deployments:
                        raise RouterBuildError("no deployments configured")
                    self._router = Router(
                        model_list=self._deployments,
                        default_litellm_params={"timeout": settings.ORCHESTRATOR_TIMEOUT_S},
                        num_retries=2,
                        allowed_fails=3,
                        retry_after=True,
                    )
        return self._router

    async def acompletion(self, model: str, messages: list[dict], **kwargs: Any) -> Any:
        router = await self._ensure()
        return await router.acompletion(model=model, messages=messages, **kwargs)

    async def astream(self, model: str, messages: list[dict], **kwargs: Any) -> Any:
        router = await self._ensure()
        return await router.acompletion(model=model, messages=messages, stream=True, **kwargs)


class OrchestratingProvider(ModelProvider):
    """Failover-capable provider backed by LiteLLM Router."""

    name = "orchestrator"

    def __init__(
        self,
        registry: ProviderRegistry | None = None,
        *,
        router_factory: Any = None,
    ) -> None:
        self._registry = registry or ProviderRegistry()
        self._mock = MockProvider()
        self._router_factory = router_factory
        self._router: _Router | None = None
        self._last_served: tuple[str, str] | None = None
        self._failover_count = 0
        self._first_try_success = 0
        self._total_attempts = 0

    def _resolve_keys(self) -> dict[str, list[str]]:
        return {
            "openai": settings.openai_keys(),
            "gemini": settings.gemini_keys(),
            "groq": settings.groq_keys(),
            "mistral": settings.mistral_keys(),
            "sambanova": settings.sambanova_keys(),
            "openrouter": settings.openrouter_keys(),
            "huggingface": settings.huggingface_keys(),
            "cohere": settings.cohere_keys(),
            "cloudflare": settings.cloudflare_keys(),
        }

    def _wire_router(self) -> _Router:
        if self._router_factory is not None:
            router = self._router_factory()
            if router is None:
                raise RouterBuildError("router_factory returned None")
            return router
        keys_by_provider = self._resolve_keys()
        deployments = _build_litellm_deployments(keys_by_provider)
        return _Router(deployments)

    def _get_router(self) -> _Router:
        if self._router is None:
            self._router = self._wire_router()
        return self._router

    def available(self) -> bool:
        try:
            if self._router_factory is not None:
                return True
            keys_by_provider = {
                name: [k for k in [settings.__dict__.get(f"{name.upper()}_API_KEY")] if k]
                for name in [
                    "openai", "gemini", "groq", "mistral", "sambanova",
                    "openrouter", "huggingface", "cohere", "cloudflare"
                ]
            }
            return bool(_build_litellm_deployments({k: v for k, v in keys_by_provider.items() if v}))
        except Exception:
            return False

    def list_models(self) -> list[ModelDescriptor]:
        return list_all_models()

    def last_served(self) -> tuple[str, str] | None:
        return self._last_served

    def _preferred_model(self, preferred: str | None) -> str:
        if preferred:
            provider = self._registry.active_name
            candidate = f"{provider}/{preferred}" if provider != "openai" else preferred
            if get_capability(provider, preferred) is not None:
                return candidate
            return get_default_model(provider)
        return get_default_model(self._registry.active_name)

    def _capability_filter(
        self,
        models: list[str],
        tools: list[dict] | None,
        context_estimate: int = 0,
    ) -> list[str]:
        out: list[str] = []
        for model in models:
            provider = self._registry.active_name
            model_id = model.split("/")[-1] if "/" in model else model
            cap = get_capability(provider, model_id)
            if cap is None:
                continue
            if tools and not cap.get("tools"):
                continue
            if cap.get("context_window") and context_estimate > cap["context_window"]:
                continue
            out.append(model)
        return out

    async def _chat_once(self, router: _Router, model: str, messages: list[dict], **kwargs: Any) -> Any:
        self._total_attempts += 1
        try:
            resp = await router.acompletion(model=model, messages=messages, **kwargs)
            self._first_try_success += 1
            return resp
        except Exception:
            self._failover_count += 1
            raise

    async def chat(
        self,
        messages: Iterable[ChatMessage],
        *,
        model: str | None = None,
        system_prompt: str | None = None,
        tools: list[dict] | None = None,
    ) -> str | ChatMessage:
        wire = self._wire_messages(messages, system_prompt)
        router = self._get_router()
        preferred = self._preferred_model(model)
        context_estimate = sum(len(m.content or "") for m in messages)
        candidates = self._capability_filter([preferred], tools, context_estimate)
        if not candidates:
            candidates = self._capability_filter(
                list_models(self._registry.active_name), tools, context_estimate
            )
        if not candidates:
            raise NoCandidateError("no candidates satisfy tools/context constraints")

        last_exc: Exception | None = None
        for idx, candidate in enumerate(candidates[: settings.ORCHESTRATOR_MAX_FAILOVERS + 1]):
            try:
                response = await self._chat_once(
                    router,
                    candidate,
                    wire,
                    tools=tools or None,
                )
                choice = response.choices[0].message
                provider = candidate.split("/")[0] if "/" in candidate else self._registry.active_name
                self._last_served = (provider, candidate)
                if getattr(choice, "tool_calls", None):
                    return ChatMessage(
                        role="assistant",
                        content=getattr(choice, "content", None),
                        tool_calls=[tc.dict() for tc in getattr(choice, "tool_calls")],
                    )
                return choice.content or ""
            except Exception as exc:
                last_exc = exc
                if idx < settings.ORCHESTRATOR_MAX_FAILOVERS:
                    continue
                break

        if last_exc is not None:
            logger.warning("orchestrator exhausting to mock: %s", last_exc)
        self._last_served = ("mock", "mock-echo")
        return await self._mock.chat(messages, model=model, system_prompt=system_prompt, tools=tools)

    async def stream(
        self,
        messages: Iterable[ChatMessage],
        *,
        model: str | None = None,
        system_prompt: str | None = None,
        tools: list[dict] | None = None,
    ) -> AsyncIterator[str | ChatMessage]:
        wire = self._wire_messages(messages, system_prompt)
        router = self._get_router()
        preferred = self._preferred_model(model)
        context_estimate = sum(len(m.content or "") for m in messages)
        candidates = self._capability_filter([preferred], tools, context_estimate)
        if not candidates:
            candidates = self._capability_filter(
                list_models(self._registry.active_name), tools, context_estimate
            )
        if not candidates:
            raise NoCandidateError("no candidates satisfy tools/context constraints")

        last_exc: Exception | None = None
        for idx, candidate in enumerate(candidates[: settings.ORCHESTRATOR_MAX_FAILOVERS + 1]):
            try:
                gen = await router.astream(model=candidate, messages=wire, tools=tools or None)
                provider = candidate.split("/")[0] if "/" in candidate else self._registry.active_name
                self._last_served = (provider, candidate)
                async for chunk in gen:
                    delta = chunk.choices[0].delta
                    if getattr(delta, "tool_calls", None):
                        yield ChatMessage(
                            role="assistant",
                            content=getattr(delta, "content", None),
                            tool_calls=[tc.dict() for tc in getattr(delta, "tool_calls")],
                        )
                        return
                    token = getattr(delta, "content", None)
                    if token:
                        yield token
                return
            except Exception as exc:
                last_exc = exc
                if idx < settings.ORCHESTRATOR_MAX_FAILOVERS:
                    continue
                break

        if last_exc is not None:
            logger.warning("orchestrator stream exhausting to mock: %s", last_exc)
        self._last_served = ("mock", "mock-echo")
        async for chunk in self._mock.stream(messages, model=model, system_prompt=system_prompt, tools=tools):
            yield chunk

    @staticmethod
    def _wire_messages(messages: Iterable[ChatMessage], system_prompt: str | None) -> list[dict]:
        wire: list[dict[str, Any]] = []
        if system_prompt:
            wire.append({"role": "system", "content": system_prompt})
        for m in messages:
            role = m.role if m.role in ("system", "user", "assistant", "tool") else "user"
            msg: dict[str, Any] = {"role": role, "content": m.content or ""}
            if m.tool_calls:
                msg["tool_calls"] = m.tool_calls
            if m.tool_call_id:
                msg["tool_call_id"] = m.tool_call_id
            wire.append(msg)
        return wire

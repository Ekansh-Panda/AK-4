"""Provider listing, status and active-provider selection endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.auth import get_current_user
from app.db.session import get_db
from app.schemas.provider import (
    ActiveProviderOut,
    ModelInfo,
    ProviderInfo,
    ProviderStatus,
    SetActiveProvider,
)
from app.services.providers.capability_matrix import list_models as list_models_from_matrix
from app.services.providers.registry import registry

router = APIRouter(prefix="/providers", tags=["providers"])


def _models(provider_name: str) -> list[ModelInfo]:
    return [
        ModelInfo(
            id=m.id, name=m.name, provider=m.provider, context_window=m.context_window
        )
        for m in list_models_from_matrix(provider_name)
    ]


@router.get("", response_model=list[ProviderInfo])
def list_providers(user_id: str = Depends(get_current_user)) -> list[ProviderInfo]:
    active = registry.active_name
    out: list[ProviderInfo] = []
    for provider in registry.list():
        avail = provider.available()
        out.append(
            ProviderInfo(
                name=provider.name,
                description=f"{provider.name} model provider",
                available=avail,
                configured=avail,
                active=provider.name == active,
                models=_models(provider.name),
            )
        )
    return out


@router.get("/models", response_model=list[ModelInfo])
def list_models(user_id: str = Depends(get_current_user)) -> list[ModelInfo]:
    """Models for the *active* provider (the one chat will use)."""
    active = registry.get()
    return _models(active.name)


@router.get("/status", response_model=list[ProviderStatus])
def provider_status(user_id: str = Depends(get_current_user)) -> list[ProviderStatus]:
    active = registry.active_name
    ping_cache = registry._read_ping_cache()
    return [
        ProviderStatus(
            name=a.name,
            configured=a.configured,
            available=a.available,
            active=a.name == active,
            reachable=ping_cache.get(a.name),
        )
        for a in registry.availability()
    ]


@router.get("/ping")
async def ping_providers(
    refresh: bool = False, user_id: str = Depends(get_current_user)
) -> dict[str, bool]:
    """Ping all configured providers. Returns cached results when fresh."""
    return await registry.ping_with_cache(force_refresh=refresh)


@router.put("/active", response_model=ActiveProviderOut)
def set_active_provider(
    body: SetActiveProvider,
    user_id: str = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ActiveProviderOut:
    if not registry.has(body.name):
        raise HTTPException(status_code=404, detail=f"unknown provider '{body.name}'")
    name = registry.persist_active(db, body.name)
    return ActiveProviderOut(active=name)


@router.get("/orchestrator/status")
def orchestrator_status(user_id: str = Depends(get_current_user)) -> dict:
    """Observability for the LiteLLM orchestrator."""
    from app.services.providers.orchestrator import OrchestratingProvider
    from app.services.providers.registry import registry as provider_registry

    orch = OrchestratingProvider(registry=provider_registry)
    ls = orch.last_served()
    total = orch._total_attempts or 1
    return {
        "enabled": True,
        "available": orch.available(),
        "last_served": {
            "provider": ls[0] if ls else None,
            "model": ls[1] if ls else None,
        },
        "counters": {
            "first_try_success_ratio": orch._first_try_success / total,
            "failovers_total": orch._failover_count,
            "total_attempts": orch._total_attempts,
        },
    }


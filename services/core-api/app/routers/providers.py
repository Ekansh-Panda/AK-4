"""Provider listing, status and active-provider selection endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.provider import (
    ActiveProviderOut,
    ModelInfo,
    ProviderInfo,
    ProviderStatus,
    SetActiveProvider,
)
from app.services.providers.registry import registry

router = APIRouter(prefix="/providers", tags=["providers"])


def _models(provider) -> list[ModelInfo]:
    return [
        ModelInfo(
            id=m.id, name=m.name, provider=m.provider, context_window=m.context_window
        )
        for m in provider.list_models()
    ]


@router.get("", response_model=list[ProviderInfo])
def list_providers() -> list[ProviderInfo]:
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
                models=_models(provider),
            )
        )
    return out


@router.get("/models", response_model=list[ModelInfo])
def list_models() -> list[ModelInfo]:
    """Models for the *active* provider (the one chat will use)."""
    return _models(registry.get())


@router.get("/status", response_model=list[ProviderStatus])
def provider_status() -> list[ProviderStatus]:
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
async def ping_providers(refresh: bool = False) -> dict[str, bool]:
    """Ping all configured providers. Returns cached results when fresh."""
    return await registry.ping_with_cache(force_refresh=refresh)


@router.put("/active", response_model=ActiveProviderOut)
def set_active_provider(
    body: SetActiveProvider, db: Session = Depends(get_db)
) -> ActiveProviderOut:
    if not registry.has(body.name):
        raise HTTPException(status_code=404, detail=f"unknown provider '{body.name}'")
    name = registry.persist_active(db, body.name)
    return ActiveProviderOut(active=name)

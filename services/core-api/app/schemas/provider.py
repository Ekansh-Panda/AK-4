"""Provider schemas."""

from __future__ import annotations

from pydantic import BaseModel


class ModelInfo(BaseModel):
    id: str
    name: str
    provider: str
    context_window: int | None = None


class ProviderInfo(BaseModel):
    name: str
    description: str
    available: bool = True
    configured: bool = False
    active: bool = False
    models: list[ModelInfo] = []


class ProviderStatus(BaseModel):
    name: str
    configured: bool
    available: bool
    active: bool = False
    reachable: bool | None = None


class SetActiveProvider(BaseModel):
    name: str


class ActiveProviderOut(BaseModel):
    active: str

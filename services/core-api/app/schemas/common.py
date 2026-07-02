"""Shared Pydantic base schemas."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict


class ORMModel(BaseModel):
    """Base for schemas that read from ORM objects."""

    model_config = ConfigDict(from_attributes=True)


class TimestampedORMModel(ORMModel):
    id: str
    created_at: datetime
    updated_at: datetime


class StatusResponse(BaseModel):
    status: str = "ok"
    detail: str | None = None

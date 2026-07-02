"""Task schemas."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field

from app.schemas.common import TimestampedORMModel


class TaskCreate(BaseModel):
    title: str = Field(..., min_length=1)
    description: str | None = None
    user_id: str | None = None
    due_at: datetime | None = None


class TaskUpdate(BaseModel):
    title: str | None = None
    description: str | None = None
    status: str | None = None
    due_at: datetime | None = None


class TaskOut(TimestampedORMModel):
    user_id: str | None = None
    title: str
    description: str | None = None
    status: str
    due_at: datetime | None = None

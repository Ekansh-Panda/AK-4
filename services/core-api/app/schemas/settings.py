"""Settings schemas."""

from __future__ import annotations

from pydantic import BaseModel

from app.schemas.common import TimestampedORMModel


class SettingUpsert(BaseModel):
    key: str
    value: str | None = None


class SettingOut(TimestampedORMModel):
    key: str
    value: str | None = None

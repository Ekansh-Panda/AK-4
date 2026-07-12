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


class ComputerUseSettings(BaseModel):
    trust_level: str = "manual"
    max_steps: int = 50
    plan_timeout_s: int = 600
    vision_enabled: bool = True
    audio_enabled: bool = False
    double_verify: bool = True
    browser_enabled: bool = False

"""Plan and step schemas."""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel

from app.schemas.common import TimestampedORMModel


class PlanStepCreate(BaseModel):
    action: str
    args_json: str | dict[str, Any] | None = None
    parent_step_id: str | None = None
    step_order: int = 0


class PlanStepOut(TimestampedORMModel):
    id: str
    plan_id: str
    parent_step_id: str | None = None
    step_order: int
    action: str
    args_json: str | None = None
    status: str
    result: str | None = None
    error: str | None = None
    retries: int
    screencap_path: str | None = None
    completed_at: datetime | None = None


class PlanCreate(BaseModel):
    goal: str
    parallel: bool = False
    trust_level: str = "manual"
    steps: list[PlanStepCreate] | None = None


class PlanOut(TimestampedORMModel):
    id: str
    user_id: str
    device_id: str
    goal: str
    trust_level: str
    status: str
    parallel: bool
    completed_at: datetime | None = None
    error: str | None = None


class PlanDetail(PlanOut):
    steps: list[PlanStepOut] = []


class SubPlanCreate(BaseModel):
    parent_step_id: str
    goal: str
    trust_level: str = "manual"

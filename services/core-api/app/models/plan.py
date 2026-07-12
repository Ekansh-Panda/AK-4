"""Plan and step models for computer-control execution plans."""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, String, Text, Boolean, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin, UUIDMixin


class TaskPlan(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "task_plans"

    user_id: Mapped[str] = mapped_column(String(36), index=True)
    device_id: Mapped[str] = mapped_column(String(36), index=True)
    goal: Mapped[str] = mapped_column(Text)
    trust_level: Mapped[str] = mapped_column(String(32), default="manual")
    status: Mapped[str] = mapped_column(String(32), default="pending", index=True)
    parallel: Mapped[bool] = mapped_column(Boolean, default=False)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    error: Mapped[Optional[str]] = mapped_column(Text, nullable=True)


class PlanStep(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "plan_steps"

    plan_id: Mapped[str] = mapped_column(String(36), ForeignKey("task_plans.id"), index=True)
    parent_step_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True, index=True)
    step_order: Mapped[int] = mapped_column(default=0)
    action: Mapped[str] = mapped_column(String(128))
    args_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(32), default="pending", index=True)
    result: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    error: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    retries: Mapped[int] = mapped_column(default=0)
    screencap_path: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

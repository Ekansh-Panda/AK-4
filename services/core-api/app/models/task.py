"""Task model.

TODO(Khoj/APScheduler): add scheduling fields (cron, next_run) when the
background scheduler is wired in.
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin, UUIDMixin


class Task(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "tasks"

    user_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("users.id"), nullable=True, index=True
    )
    title: Mapped[str] = mapped_column(String(255))
    project_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("projects.id"), nullable=True, index=True
    )
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    # "pending" | "in_progress" | "done" | "cancelled"
    status: Mapped[str] = mapped_column(String(32), default="pending", index=True)
    due_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

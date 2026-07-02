"""Project model — long-running workspace / brief."""

from __future__ import annotations

from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin, UUIDMixin


class Project(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "projects"

    user_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("users.id"), nullable=True, index=True
    )
    name: Mapped[str] = mapped_column(String(255))
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    # "active" | "archived" | "completed"
    status: Mapped[str] = mapped_column(String(32), default="active", index=True)
    # Free-form JSON-ish notes for the AI to hold context.
    brief: Mapped[str | None] = mapped_column(Text, nullable=True)

"""Research model — stored deep-dive sessions with cited findings."""

from __future__ import annotations

from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin, UUIDMixin


class Research(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "research"

    user_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("users.id"), nullable=True, index=True
    )
    query: Mapped[str] = mapped_column(String(1024))
    # "pending" | "running" | "done" | "failed"
    status: Mapped[str] = mapped_column(String(32), default="pending", index=True)
    # The raw findings text (Markdown with citations).
    findings: Mapped[str | None] = mapped_column(Text, nullable=True)
    # JSON-encoded list of source URLs or references.
    sources: Mapped[str | None] = mapped_column(Text, nullable=True)

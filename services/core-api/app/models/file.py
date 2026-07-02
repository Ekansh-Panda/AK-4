"""Uploaded file metadata model."""

from __future__ import annotations

from sqlalchemy import ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin, UUIDMixin


class FileRecord(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "files"

    user_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("users.id"), nullable=True, index=True
    )
    filename: Mapped[str] = mapped_column(String(255))
    content_type: Mapped[str | None] = mapped_column(String(128), nullable=True)
    size_bytes: Mapped[int] = mapped_column(Integer, default=0)
    storage_path: Mapped[str] = mapped_column(String(1024))
    # "uploaded" | "ingesting" | "ingested" | "failed"
    status: Mapped[str] = mapped_column(String(32), default="uploaded")
    # Best-effort extracted text for supported types (None for binary/unknown).
    extracted_text: Mapped[str | None] = mapped_column(Text, nullable=True)

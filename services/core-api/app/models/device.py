"""Remote device model with pairing support.

Devices store a hashed pairing secret so remote dashboards can authenticate
over REST and WS without transmitting the raw code after initial exchange.
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin, UUIDMixin


class Device(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "devices"

    user_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("users.id"), nullable=True, index=True
    )
    name: Mapped[str] = mapped_column(String(128))
    platform: Mapped[str | None] = mapped_column(String(32), nullable=True)
    # "online" | "offline" | "sleeping"
    state: Mapped[str] = mapped_column(String(16), default="offline")
    is_paired: Mapped[bool] = mapped_column(Boolean, default=False)
    last_seen_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    # --- Pairing ---
    # SHA-256 hex digest of the pairing token. Null until paired.
    pairing_secret_hash: Mapped[str | None] = mapped_column(
        String(64), nullable=True, default=None
    )
    # Bearer token issued on successful pairing (stored to validate remote WS).
    bearer_token: Mapped[str | None] = mapped_column(
        Text, nullable=True, default=None
    )

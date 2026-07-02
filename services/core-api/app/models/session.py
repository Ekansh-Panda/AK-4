"""Chat session model.

Named ``ChatSession`` to avoid clashing with SQLAlchemy's ``Session`` and the
``session`` module name in the stdlib / db layer.
"""

from __future__ import annotations

from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin, UUIDMixin


class ChatSession(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "chat_sessions"

    user_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("users.id"), nullable=True, index=True
    )
    title: Mapped[str] = mapped_column(String(255), default="New chat")
    # Persona mode used for this session (friend/operator/researcher/coder).
    persona_mode: Mapped[str] = mapped_column(String(32), default="friend")

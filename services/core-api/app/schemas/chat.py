"""Chat schemas."""

from __future__ import annotations

from pydantic import BaseModel, Field

from app.schemas.common import TimestampedORMModel


class MessageOut(TimestampedORMModel):
    session_id: str
    role: str
    content: str
    model: str | None = None


class ChatSessionOut(TimestampedORMModel):
    user_id: str | None = None
    title: str
    persona_mode: str


class ChatSessionCreate(BaseModel):
    title: str = "New chat"
    persona_mode: str = "friend"
    user_id: str | None = None


class ChatRequest(BaseModel):
    """A single-turn chat request."""

    message: str = Field(..., min_length=1)
    session_id: str | None = None
    model: str | None = None
    persona_mode: str | None = None


class ChatResponse(BaseModel):
    session_id: str
    reply: MessageOut

"""Chat REST endpoints.

POST /api/chat returns a mock assistant reply (token streaming lives at
/ws/chat).
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.auth import get_current_user
from app.db.session import get_db
from app.schemas.chat import (
    ChatRequest,
    ChatResponse,
    ChatSessionCreate,
    ChatSessionOut,
    MessageOut,
)
from app.services.chat_service import ChatService

router = APIRouter(prefix="/chat", tags=["chat"])


@router.post("", response_model=ChatResponse)
async def chat(
    req: ChatRequest,
    db: Session = Depends(get_db),
    user_id: str = Depends(get_current_user),
) -> ChatResponse:
    service = ChatService(db)
    session, reply = await service.respond(
        session_id=req.session_id,
        user_text=req.message,
        model=req.model,
        persona_mode=req.persona_mode,
        user_id=user_id,
    )
    return ChatResponse(
        session_id=session.id, reply=MessageOut.model_validate(reply)
    )


@router.post("/sessions", response_model=ChatSessionOut)
def create_session(
    body: ChatSessionCreate,
    db: Session = Depends(get_db),
    user_id: str = Depends(get_current_user),
) -> ChatSessionOut:
    service = ChatService(db)
    session = service.get_or_create_session(
        None, persona_mode=body.persona_mode, user_id=user_id
    )
    if body.title:
        session.title = body.title
        db.commit()
        db.refresh(session)
    return ChatSessionOut.model_validate(session)


@router.get("/sessions/{session_id}/messages", response_model=list[MessageOut])
def session_messages(
    session_id: str,
    db: Session = Depends(get_db),
    user_id: str = Depends(get_current_user),
) -> list[MessageOut]:
    service = ChatService(db)
    if service.get_owned_session(session_id, user_id) is None:
        raise HTTPException(status_code=404, detail="session not found")
    return [MessageOut.model_validate(m) for m in service.history(session_id)]

"""/ws/chat — token-by-token streaming chat over the ACTIVE model provider.

Streams via the active provider's ``stream()`` (mock fallback on missing key or
provider error). Frame protocol is stable for the desktop client.

Client sends JSON: {"message": "...", "session_id": "...?", "persona_mode": "...?"}
Server streams JSON frames:
  {"type": "session", "session_id": "..."}
  {"type": "token", "token": "..."}
  {"type": "error", "detail": "..."}
  {"type": "done", "session_id": "..."}
"""

from __future__ import annotations

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.core.logging import get_logger
from app.db.session import SessionLocal
from app.services.chat_service import ChatService
from app.ws import manager

logger = get_logger(__name__)
router = APIRouter()

CHANNEL = "chat"


@router.websocket("/ws/chat")
async def ws_chat(websocket: WebSocket) -> None:
    await manager.connect(CHANNEL, websocket)
    try:
        while True:
            payload = await websocket.receive_json()
            user_text = (payload or {}).get("message", "").strip()
            if not user_text:
                await websocket.send_json(
                    {"type": "error", "detail": "empty message"}
                )
                continue

            # New DB session per turn keeps things simple and thread-safe.
            db = SessionLocal()
            try:
                chat = ChatService(db)
                async for kind, value in chat.stream_response(
                    session_id=payload.get("session_id"),
                    user_text=user_text,
                    model=payload.get("model"),
                    persona_mode=payload.get("persona_mode"),
                ):
                    if kind == "session":
                        await websocket.send_json(
                            {"type": "session", "session_id": value}
                        )
                    elif kind == "token":
                        await websocket.send_json({"type": "token", "token": value})
                    elif kind == "error":
                        await websocket.send_json({"type": "error", "detail": value})
                    elif kind == "done":
                        await websocket.send_json(
                            {"type": "done", "session_id": value}
                        )
            finally:
                db.close()
    except WebSocketDisconnect:
        manager.disconnect(CHANNEL, websocket)
    except Exception as exc:  # noqa: BLE001
        logger.exception("ws_chat error: %s", exc)
        manager.disconnect(CHANNEL, websocket)

"""/ws/status — periodic heartbeat the desktop/remote UIs can subscribe to."""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.core.config import settings
from app.ws import manager

router = APIRouter()

CHANNEL = "status"


@router.websocket("/ws/status")
async def ws_status(websocket: WebSocket) -> None:
    if settings.MIORI_API_TOKEN:
        token = websocket.query_params.get("token")
        if not token:
            auth = websocket.headers.get("authorization", "")
            if auth.lower().startswith("bearer "):
                token = auth[7:].strip()
        if token != settings.MIORI_API_TOKEN:
            await websocket.close(code=4003, reason="authentication required")
            return

    await manager.connect(CHANNEL, websocket)
    try:
        while True:
            await websocket.send_json(
                {
                    "type": "heartbeat",
                    "app": settings.APP_NAME,
                    "version": settings.APP_VERSION,
                    "lite_mode": settings.LITE_MODE,
                    "remote_enabled": settings.REMOTE_ENABLED,
                    "ts": datetime.now(timezone.utc).isoformat(),
                }
            )
            await asyncio.sleep(5)
    except WebSocketDisconnect:
        manager.disconnect(CHANNEL, websocket)

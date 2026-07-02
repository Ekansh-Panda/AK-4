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

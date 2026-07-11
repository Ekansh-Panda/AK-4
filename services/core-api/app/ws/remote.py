"""/ws/remote — authenticated command relay and presence channel.

Protocol:
  Client → Server:
    {"type": "presence"}             → triggers presence broadcast
    {"type": "command", "action": "...", "device_id": "...", ...}
                                     → relayed to all other connected clients

  Server → Client:
    {"type": "presence", "connected": N, "devices": [...]}
    {"type": "command", "action": "...", "device_id": "...", ...}
    {"type": "error", "detail": "..."}

Authentication: pass `token` query parameter with a valid device bearer token,
or set Authorization header. Unauthenticated connections are accepted but
marked as "observer" (can receive broadcasts but cannot send commands) when
MIORI_API_TOKEN is not set. When MIORI_API_TOKEN is set, all connections
must authenticate.
"""

from __future__ import annotations

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from sqlalchemy import select

from app.core.config import settings
from app.core.logging import get_logger
from app.db.session import SessionLocal
from app.models.device import Device
from app.services.remote.service import _hash_secret
from app.ws import manager

logger = get_logger(__name__)
router = APIRouter()

CHANNEL = "remote"


async def _broadcast_presence() -> None:
    """Send current presence info to the status channel for the desktop UI."""
    count = manager.count(CHANNEL)
    await manager.broadcast("status", {
        "type": "presence",
        "remote_connected_count": count,
    })


def _authenticate_ws(websocket: WebSocket) -> bool:
    """Extract and validate a device bearer token from WS query params or headers.

    Checks the database to confirm the token is associated with a registered
    device. Returns True if a valid device token is found, False otherwise.
    """
    raw_token = websocket.query_params.get("token")
    if not raw_token:
        auth = websocket.headers.get("authorization", "")
        if auth.lower().startswith("bearer "):
            raw_token = auth[7:].strip()
    if not raw_token:
        return False

    with SessionLocal() as db:
        stmt = select(Device).where(Device.bearer_token == _hash_secret(raw_token))
        result = db.execute(stmt).scalar_one_or_none()
        return result is not None


@router.websocket("/ws/remote")
async def ws_remote(websocket: WebSocket) -> None:
    if not settings.REMOTE_ENABLED:
        await websocket.close(code=4003, reason="remote disabled")
        return

    is_authenticated = _authenticate_ws(websocket)

    if settings.MIORI_API_TOKEN and not is_authenticated:
        await websocket.close(code=4003, reason="invalid token")
        return

    await manager.connect(CHANNEL, websocket)
    logger.info(
        "Remote WS connected (authenticated=%s, total=%d)",
        is_authenticated,
        manager.count(CHANNEL),
    )

    # Broadcast updated presence to all clients.
    await _broadcast_presence()

    try:
        while True:
            data = await websocket.receive_json()
            msg_type = (data or {}).get("type", "")

            if msg_type == "presence":
                # Client requests a presence refresh.
                await _broadcast_presence()

            elif msg_type == "command":
                if not is_authenticated:
                    await websocket.send_json({
                        "type": "error",
                        "detail": "authentication required for commands",
                    })
                    continue

                # Relay the command to all connected clients (including sender
                # for confirmation / UI update).
                await manager.broadcast(CHANNEL, data)
                logger.info(
                    "Remote command relayed: action=%s device=%s",
                    data.get("action"),
                    data.get("device_id"),
                )

            elif msg_type == "frame":
                if not is_authenticated:
                    await websocket.send_json({
                        "type": "error",
                        "detail": "authentication required for computer-use",
                    })
                    continue

                from app.services.computer_use import run_tool
                action = data.get("action")
                args = data.get("args", {})
                try:
                    result = run_tool(action, args)
                    await websocket.send_json({
                        "type": "frame_result",
                        "status": "success",
                        "result": result,
                    })
                except Exception as exc:
                    await websocket.send_json({
                        "type": "frame_result",
                        "status": "error",
                        "error": str(exc),
                    })

            else:
                await websocket.send_json({
                    "type": "error",
                    "detail": f"unknown message type: {msg_type}",
                })

    except WebSocketDisconnect:
        manager.disconnect(CHANNEL, websocket)
        logger.info(
            "Remote WS disconnected (total=%d)", manager.count(CHANNEL)
        )
        # Broadcast updated presence after disconnect.
        await _broadcast_presence()

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
marked as "observer" (can receive broadcasts but cannot send commands).
"""

from __future__ import annotations

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.core.config import settings
from app.core.logging import get_logger
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


def _authenticate_ws(websocket: WebSocket) -> str | None:
    """Extract and validate bearer token from WS query params or headers.

    Returns the token string if present (validation against DB is deferred
    to avoid importing DB session at module level). Returns None if no token.
    """
    # Check query parameter first (preferred for WS).
    token = websocket.query_params.get("token")
    if token:
        return token
    # Fall back to Authorization header.
    auth = websocket.headers.get("authorization", "")
    if auth.lower().startswith("bearer "):
        return auth[7:].strip()
    return None


@router.websocket("/ws/remote")
async def ws_remote(websocket: WebSocket) -> None:
    if not settings.REMOTE_ENABLED:
        await websocket.close(code=4003, reason="remote disabled")
        return

    token = _authenticate_ws(websocket)
    is_authenticated = token is not None

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

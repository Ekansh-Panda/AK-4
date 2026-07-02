"""WebSocket utilities and a small connection manager."""

from __future__ import annotations

from fastapi import WebSocket


class ConnectionManager:
    """Tracks active WebSocket connections per channel."""

    def __init__(self) -> None:
        self._connections: dict[str, set[WebSocket]] = {}

    async def connect(self, channel: str, websocket: WebSocket) -> None:
        await websocket.accept()
        self._connections.setdefault(channel, set()).add(websocket)

    def disconnect(self, channel: str, websocket: WebSocket) -> None:
        conns = self._connections.get(channel)
        if conns:
            conns.discard(websocket)
            if not conns:
                self._connections.pop(channel, None)

    async def broadcast(self, channel: str, message: dict) -> None:
        for ws in list(self._connections.get(channel, set())):
            try:
                await ws.send_json(message)
            except Exception:  # noqa: BLE001 - drop dead connections
                self.disconnect(channel, ws)

    def count(self, channel: str) -> int:
        return len(self._connections.get(channel, set()))


manager = ConnectionManager()

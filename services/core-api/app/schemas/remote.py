"""Remote / device schemas."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel

from app.schemas.common import TimestampedORMModel


class DeviceRegister(BaseModel):
    name: str
    platform: str | None = None
    user_id: str | None = None


class DeviceOut(TimestampedORMModel):
    user_id: str | None = None
    name: str
    platform: str | None = None
    state: str
    is_paired: bool
    last_seen_at: datetime | None = None


class RemoteSessionOut(BaseModel):
    id: str
    device_id: str
    state: str
    created_at: datetime


# --- Pairing ---

class PairingCodeOut(BaseModel):
    device_id: str
    code: str


class PairRequest(BaseModel):
    device_id: str
    code: str


class PairResponse(BaseModel):
    device_id: str
    token: str
    paired: bool = True


class PresenceOut(BaseModel):
    """Current remote presence info (connected sockets, device states)."""
    connected_devices: int
    devices: list[DeviceOut]

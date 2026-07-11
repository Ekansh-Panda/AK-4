"""Remote device + session + pairing endpoints.

Pairing flow:
  1. Desktop: POST /api/remote/devices/{id}/pairing-code → get a 6-char code
  2. Phone:   POST /api/remote/pair {device_id, code} → get a bearer token
  3. Phone:   Use bearer token in Authorization header for all subsequent requests
              and in the /ws/remote WebSocket upgrade (query param `token`)
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.auth import get_current_user
from app.db.session import get_db
from app.models.device import Device
from app.schemas.common import StatusResponse
from app.schemas.remote import (
    DeviceOut,
    DeviceRegister,
    PairingCodeOut,
    PairRequest,
    PairResponse,
    PresenceOut,
    RemoteSessionOut,
)
from app.services.remote.service import RemoteSessionService
from app.ws import manager as ws_manager

router = APIRouter(prefix="/remote", tags=["remote"])


@router.post("/devices", response_model=DeviceOut)
def register_device(
    body: DeviceRegister,
    user_id: str = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> DeviceOut:
    service = RemoteSessionService(db)
    device = service.register_device(
        body.name, platform=body.platform, user_id=body.user_id
    )
    return DeviceOut.model_validate(device)


@router.get("/devices", response_model=list[DeviceOut])
def list_devices(user_id: str = Depends(get_current_user), db: Session = Depends(get_db)) -> list[DeviceOut]:
    service = RemoteSessionService(db)
    return [DeviceOut.model_validate(d) for d in service.list_devices()]


@router.post("/devices/{device_id}/wake", response_model=DeviceOut)
async def wake_device(
    device_id: str,
    user_id: str = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> DeviceOut:
    service = RemoteSessionService(db)
    device = service.set_device_state(device_id, "online")
    if not device:
        raise HTTPException(status_code=404, detail="device not found")
    # Broadcast wake command over WS to any connected remote clients.
    await ws_manager.broadcast("remote", {
        "type": "command",
        "action": "wake",
        "device_id": device_id,
    })
    return DeviceOut.model_validate(device)


@router.post("/devices/{device_id}/sleep", response_model=DeviceOut)
async def sleep_device(
    device_id: str,
    user_id: str = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> DeviceOut:
    service = RemoteSessionService(db)
    device = service.set_device_state(device_id, "sleeping")
    if not device:
        raise HTTPException(status_code=404, detail="device not found")
    # Broadcast sleep command over WS.
    await ws_manager.broadcast("remote", {
        "type": "command",
        "action": "sleep",
        "device_id": device_id,
    })
    return DeviceOut.model_validate(device)


# --- Pairing ---

@router.post("/devices/{device_id}/pairing-code", response_model=PairingCodeOut)
def generate_pairing_code(
    device_id: str,
    user_id: str = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> PairingCodeOut:
    """Generate a 6-character pairing code for a device.

    This code is shown in the desktop Settings UI; the remote dashboard user
    enters it to complete pairing. Codes are single-use and in-memory.
    """
    service = RemoteSessionService(db)
    code = service.generate_pairing_code(device_id)
    if not code:
        raise HTTPException(status_code=404, detail="device not found")
    return PairingCodeOut(device_id=device_id, code=code)


@router.post("/pair", response_model=PairResponse)
def pair_device(
    body: PairRequest,
    user_id: str = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> PairResponse:
    """Exchange a pairing code for a bearer token.

    The remote dashboard submits the code shown on the desktop. On success,
    receives a bearer token for authenticated REST/WS access.
    """
    service = RemoteSessionService(db)
    token = service.pair_with_code(body.device_id, body.code)
    if not token:
        raise HTTPException(status_code=403, detail="invalid pairing code")
    return PairResponse(device_id=body.device_id, token=token)


@router.post("/devices/{device_id}/unpair", response_model=DeviceOut)
def unpair_device(
    device_id: str,
    user_id: str = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> DeviceOut:
    """Revoke pairing for a device, invalidating its bearer token."""
    service = RemoteSessionService(db)
    device = service.unpair_device(device_id)
    if not device:
        raise HTTPException(status_code=404, detail="device not found")
    return DeviceOut.model_validate(device)


# --- Presence ---

@router.get("/presence", response_model=PresenceOut)
def get_presence(user_id: str = Depends(get_current_user), db: Session = Depends(get_db)) -> PresenceOut:
    """Current remote presence: how many WS clients are connected + device list."""
    service = RemoteSessionService(db)
    devices = service.list_devices()
    return PresenceOut(
        connected_devices=ws_manager.count("remote"),
        devices=[DeviceOut.model_validate(d) for d in devices],
    )


# --- Sessions ---

@router.post("/devices/{device_id}/sessions", response_model=RemoteSessionOut)
def create_session(
    device_id: str,
    user_id: str = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> RemoteSessionOut:
    service = RemoteSessionService(db)
    if not db.get(Device, device_id):
        raise HTTPException(status_code=404, detail="device not found")
    session = service.create_session(device_id)
    return RemoteSessionOut(
        id=session.id,
        device_id=session.device_id,
        state=session.state,
        created_at=session.created_at,
    )


@router.get("/sessions", response_model=list[RemoteSessionOut])
def list_sessions(user_id: str = Depends(get_current_user), db: Session = Depends(get_db)) -> list[RemoteSessionOut]:
    service = RemoteSessionService(db)
    return [
        RemoteSessionOut(
            id=s.id, device_id=s.device_id, state=s.state, created_at=s.created_at
        )
        for s in service.list_sessions()
    ]


@router.delete("/sessions/{session_id}", response_model=StatusResponse)
def end_session(
    session_id: str,
    user_id: str = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> StatusResponse:
    service = RemoteSessionService(db)
    if not service.end_session(session_id):
        raise HTTPException(status_code=404, detail="session not found")
    return StatusResponse(detail="ended")

"""RemoteSessionService — device registry, pairing, and remote control sessions.

Devices are persisted in the DB. Pairing is done via a code: the host generates
a short alphanumeric code; the remote dashboard submits it to POST /api/remote/pair
and receives a bearer token. The hashed code is stored on the device row so
the raw code is never persisted.

Live remote sessions use /ws/remote with the bearer token for auth. The WS
connection manager tracks connected sockets for presence.
"""

from __future__ import annotations

import hashlib
import secrets
import uuid
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.logging import get_logger
from app.models.device import Device

logger = get_logger(__name__)


def _hash_secret(secret: str) -> str:
    """SHA-256 hex digest of a pairing secret."""
    return hashlib.sha256(secret.encode("utf-8")).hexdigest()


def _generate_pairing_code() -> str:
    """Generate a short, human-readable alphanumeric pairing code (6 chars)."""
    alphabet = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"  # no I/O/0/1 ambiguity
    return "".join(secrets.choice(alphabet) for _ in range(6))


def _generate_bearer_token() -> str:
    """Generate a cryptographically secure bearer token (URL-safe, 32 bytes)."""
    return secrets.token_urlsafe(32)


class RemoteSession:
    """Lightweight in-memory remote session record."""

    def __init__(self, device_id: str) -> None:
        self.id = str(uuid.uuid4())
        self.device_id = device_id
        self.state = "active"
        self.created_at = datetime.now(timezone.utc)


class RemoteSessionService:
    # Class-level so sessions survive across request-scoped instances.
    _sessions: dict[str, RemoteSession] = {}
    # Pending pairing codes: device_id → raw code. Short-lived, in-memory only.
    _pending_pairing_codes: dict[str, str] = {}

    def __init__(self, db: Session) -> None:
        self._db = db

    # --- devices ---
    def register_device(
        self, name: str, platform: str | None = None, user_id: str | None = None
    ) -> Device:
        device = Device(
            name=name, platform=platform, user_id=user_id, state="online"
        )
        device.last_seen_at = datetime.now(timezone.utc)
        self._db.add(device)
        self._db.commit()
        self._db.refresh(device)
        return device

    def list_devices(self) -> list[Device]:
        return list(self._db.execute(select(Device)).scalars().all())

    def get_device(self, device_id: str) -> Device | None:
        return self._db.get(Device, device_id)

    def set_device_state(self, device_id: str, state: str) -> Device | None:
        """Set state to one of online/offline/sleeping (wake/sleep)."""
        device = self._db.get(Device, device_id)
        if not device:
            return None
        device.state = state
        device.last_seen_at = datetime.now(timezone.utc)
        self._db.commit()
        self._db.refresh(device)
        return device

    # --- pairing ---
    def generate_pairing_code(self, device_id: str) -> str | None:
        """Generate a pairing code for the given device. Returns the raw code.

        The code is stored in-memory (not DB) and expires when used or when
        the server restarts. The hash is stored on the device after pairing.
        """
        device = self._db.get(Device, device_id)
        if not device:
            return None
        code = _generate_pairing_code()
        self._pending_pairing_codes[device_id] = code
        logger.info("Pairing code generated for device %s", device_id)
        return code

    def pair_with_code(self, device_id: str, code: str) -> str | None:
        """Exchange a pairing code for a bearer token.

        Returns the bearer token on success, None on failure (wrong code,
        no pending code, device not found).
        """
        pending = self._pending_pairing_codes.get(device_id)
        if not pending or pending.upper() != code.upper():
            logger.warning("Pairing failed for device %s: invalid code", device_id)
            return None

        device = self._db.get(Device, device_id)
        if not device:
            return None

        # Pairing successful: hash the code, issue a bearer token.
        token = _generate_bearer_token()
        device.pairing_secret_hash = _hash_secret(code.upper())
        device.bearer_token = token
        device.is_paired = True
        device.last_seen_at = datetime.now(timezone.utc)
        self._db.commit()
        self._db.refresh(device)

        # Consume the pending code.
        self._pending_pairing_codes.pop(device_id, None)
        logger.info("Device %s paired successfully", device_id)
        return token

    def validate_bearer_token(self, token: str) -> Device | None:
        """Look up a device by its bearer token. Returns the device if valid."""
        stmt = select(Device).where(Device.bearer_token == token)
        return self._db.execute(stmt).scalar_one_or_none()

    def unpair_device(self, device_id: str) -> Device | None:
        """Revoke pairing for a device."""
        device = self._db.get(Device, device_id)
        if not device:
            return None
        device.is_paired = False
        device.pairing_secret_hash = None
        device.bearer_token = None
        self._db.commit()
        self._db.refresh(device)
        logger.info("Device %s unpaired", device_id)
        return device

    # --- sessions ---
    def create_session(self, device_id: str) -> RemoteSession:
        session = RemoteSession(device_id)
        self._sessions[session.id] = session
        logger.info("Remote session %s created for device %s", session.id, device_id)
        return session

    def list_sessions(self) -> list[RemoteSession]:
        return list(self._sessions.values())

    def end_session(self, session_id: str) -> bool:
        return self._sessions.pop(session_id, None) is not None

"""SettingsService — thin persistence helper over the ``settings`` table.

Used wherever the app needs durable key/value config (e.g. the active provider
selection). Keeps the same DB-backed model the /settings router already uses.
"""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.setting import Setting

# Well-known keys.
ACTIVE_PROVIDER_KEY = "active_provider"
PERSONA_MODE_KEY = "persona_mode"
LITE_MODE_KEY = "lite_mode"
AGENT_MODE_KEY = "agent_mode"


class SettingsService:
    def __init__(self, db: Session) -> None:
        self._db = db

    def get(self, key: str, default: str | None = None) -> str | None:
        row = self._db.execute(
            select(Setting).where(Setting.key == key)
        ).scalar_one_or_none()
        if row is None or row.value is None:
            return default
        return row.value

    def set(self, key: str, value: str | None) -> str | None:
        row = self._db.execute(
            select(Setting).where(Setting.key == key)
        ).scalar_one_or_none()
        if row:
            row.value = value
        else:
            row = Setting(key=key, value=value)
            self._db.add(row)
        self._db.commit()
        self._db.refresh(row)
        return row.value

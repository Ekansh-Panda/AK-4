"""Current-user resolution.

Single-user identity system for local/dev use. On first boot, creates a default
user if none exists and stores the user id in settings.
"""

from __future__ import annotations

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy import select

from app.core.config import settings
from app.db.session import DEFAULT_USER_KEY, SessionLocal, ensure_default_user
from app.models.setting import Setting
from app.models.user import User

security = HTTPBearer(auto_error=False)


def get_current_user(credentials: HTTPAuthorizationCredentials | None = Depends(security)) -> str:
    """FastAPI dependency: the authenticated user's id.

    If MIORI_API_TOKEN is set, require a matching Bearer token.
    Otherwise, return the default user id from settings table.
    """
    if settings.MIORI_API_TOKEN:
        if not credentials or credentials.credentials != settings.MIORI_API_TOKEN:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or missing authentication token",
                headers={"WWW-Authenticate": "Bearer"},
            )

    with SessionLocal() as db:
        result = db.execute(
            select(Setting).where(Setting.key == DEFAULT_USER_KEY)
        ).scalar_one_or_none()
        if result and result.value:
            return result.value
        # Legacy DBs may already have a user but no `default_user_id` setting
        # (ensure_default_user early-returns when any user exists). Fall back to
        # the first user so user-scoped queries still resolve instead of
        # receiving a None user_id.
        user = db.execute(
            select(User).order_by(User.created_at).limit(1)
        ).scalar_one_or_none()
        if user:
            return user.id
    return None

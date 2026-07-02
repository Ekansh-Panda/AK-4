"""Current-user resolution.

Stub for now: returns a single fixed local user id so the rest of the app can be
written against a real ``user_id`` dependency. Phase 5 (auth.py + security.py)
replaces ``get_current_user`` with JWT/device-token verification without changing
any call sites.
"""

from __future__ import annotations

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from app.core.config import settings

# Stable local/dev user id. A real users row isn't required (SQLite doesn't
# enforce FKs by default), but ensure_dev_user() can create one if needed.
DEV_USER_ID = "00000000-0000-0000-0000-000000000001"

security = HTTPBearer(auto_error=False)

def get_current_user(credentials: HTTPAuthorizationCredentials | None = Depends(security)) -> str:
    """FastAPI dependency: the authenticated user's id.
    
    If MIORI_API_TOKEN is set in the environment, require a matching Bearer token.
    Otherwise, open (returns the dev user ID).
    """
    if settings.MIORI_API_TOKEN:
        if not credentials or credentials.credentials != settings.MIORI_API_TOKEN:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or missing authentication token",
                headers={"WWW-Authenticate": "Bearer"},
            )
    return DEV_USER_ID

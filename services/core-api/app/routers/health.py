"""Health and meta endpoints."""

from __future__ import annotations

from fastapi import APIRouter

from app.core.config import settings

router = APIRouter(tags=["health"])


@router.get("/health")
def health() -> dict:
    return {
        "status": "ok",
        "app": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "lite_mode": settings.LITE_MODE,
        "remote_enabled": settings.REMOTE_ENABLED,
    }

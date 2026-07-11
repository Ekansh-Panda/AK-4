"""Persona endpoints.

PersonaService is stateless; per-session mode lives on ChatSession. These
endpoints expose the persona profile + the *default* mode for new sessions,
persisted in the settings table (no global mutable singleton).
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.auth import get_current_user
from app.db.session import get_db
from app.schemas.persona import PersonaModeUpdate, PersonaOut
from app.services.persona.service import DEFAULT_MODE, PersonaService
from app.services.settings_service import PERSONA_MODE_KEY, SettingsService

router = APIRouter(prefix="/persona", tags=["persona"])


def _default_mode(db: Session) -> str:
    stored = SettingsService(db).get(PERSONA_MODE_KEY)
    return PersonaService.normalize_mode(stored or DEFAULT_MODE)


def _persona_out(db: Session, mode: str) -> PersonaOut:
    svc = PersonaService()
    cfg = svc.get_persona()
    return PersonaOut(
        name=cfg.name,
        tone=cfg.tone,
        relationship_mode=cfg.relationship_mode,
        verbosity=cfg.verbosity,
        humor_level=cfg.humor_level,
        operator_mode_style=cfg.operator_mode_style,
        voice_profile=cfg.voice_profile,
        presence_theme=cfg.presence_theme,
        active_mode=mode,
        system_prompt=svc.build_prompt(mode),
    )


@router.get("", response_model=PersonaOut)
def get_persona(
    user_id: str = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> PersonaOut:
    return _persona_out(db, _default_mode(db))


@router.get("/modes", response_model=list[str])
def list_modes(user_id: str = Depends(get_current_user)) -> list[str]:
    return PersonaService().list_modes()


@router.post("/mode", response_model=PersonaOut)
def set_mode(
    body: PersonaModeUpdate,
    user_id: str = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> PersonaOut:
    if not PersonaService.is_valid_mode(body.mode):
        raise HTTPException(status_code=400, detail=f"Unknown persona mode '{body.mode}'")
    SettingsService(db).set(PERSONA_MODE_KEY, body.mode)
    return _persona_out(db, body.mode)

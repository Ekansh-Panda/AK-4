"""Persona API schemas (request/response wrappers).

The canonical persona config dataclass lives in
``app.services.persona.schema`` to keep the service self-contained; these
schemas are thin API mirrors.
"""

from __future__ import annotations

from pydantic import BaseModel


class PersonaModeUpdate(BaseModel):
    mode: str


class PersonaOut(BaseModel):
    name: str
    tone: str
    relationship_mode: str
    verbosity: str
    humor_level: int
    operator_mode_style: str
    voice_profile: str
    presence_theme: str
    active_mode: str
    system_prompt: str

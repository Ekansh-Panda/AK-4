"""Audio (STT/TTS) endpoints (Mocked for Phase 6)."""

from __future__ import annotations

from fastapi import APIRouter, File, HTTPException, UploadFile
from fastapi.responses import JSONResponse, Response
from pydantic import BaseModel

from app.services.providers.voice import registry as voice_registry

router = APIRouter(prefix="/audio", tags=["audio"])


class SynthesizeRequest(BaseModel):
    text: str
    voice: str | None = None


@router.post("/transcribe")
async def transcribe_audio(file: UploadFile = File(...)) -> JSONResponse:
    provider = voice_registry.get()
    try:
        data = await file.read()
        text = await provider.transcribe(data, file.content_type or "audio/webm")
        return JSONResponse({"text": text})
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.post("/synthesize")
async def synthesize_audio(body: SynthesizeRequest) -> Response:
    provider = voice_registry.get()
    try:
        audio_bytes = await provider.synthesize(body.text, body.voice)
        if not audio_bytes:
            # Mock fallback behavior
            raise HTTPException(status_code=404, detail="TTS engine not configured (Phase 6 mock)")
        return Response(content=audio_bytes, media_type="audio/mpeg")
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))

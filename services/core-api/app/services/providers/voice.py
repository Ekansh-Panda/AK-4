"""Voice providers (STT/TTS)."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)


class VoiceProvider(ABC):
    """Base for voice transcription and synthesis."""

    name: str

    @abstractmethod
    def available(self) -> bool:
        """True if dependencies and credentials are present."""
        pass

    @abstractmethod
    async def transcribe(self, audio_data: bytes, content_type: str) -> str:
        """Transcribe audio bytes to text."""
        pass

    @abstractmethod
    async def synthesize(self, text: str, voice: str | None = None) -> bytes:
        """Synthesize text to audio bytes."""
        pass


class MockVoiceProvider(VoiceProvider):
    name = "mock"

    def available(self) -> bool:
        return True

    async def transcribe(self, audio_data: bytes, content_type: str) -> str:
        logger.info("Mock STT: returning canned transcription.")
        return "This is a mock transcription (no active STT engine)."

    async def synthesize(self, text: str, voice: str | None = None) -> bytes:
        logger.info("Mock TTS: %s", text)
        # Return a tiny valid MP3 or WAV header if we wanted to be robust,
        # but for mock we can just return empty bytes or raise.
        # Returning empty to simulate "no audio".
        return b""


class OpenAIVoiceProvider(VoiceProvider):
    name = "openai"

    def __init__(self) -> None:
        self.api_key = settings.OPENAI_API_KEY
        self.base_url = (settings.OPENAI_BASE_URL or "https://api.openai.com/v1").rstrip("/")

    def available(self) -> bool:
        return bool(self.api_key)

    async def transcribe(self, audio_data: bytes, content_type: str) -> str:
        if not self.available():
            raise RuntimeError("OpenAI API key missing")

        import httpx  # Lazy import

        url = f"{self.base_url}/audio/transcriptions"
        headers = {"Authorization": f"Bearer {self.api_key}"}
        
        filename = "audio.webm" if "webm" in content_type else "audio.wav"
        files = {"file": (filename, audio_data, content_type)}
        data = {"model": "whisper-1"}

        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(url, headers=headers, files=files, data=data)
            resp.raise_for_status()
            return resp.json().get("text", "")

    async def synthesize(self, text: str, voice: str | None = None) -> bytes:
        if not self.available():
            raise RuntimeError("OpenAI API key missing")

        import httpx  # Lazy import

        url = f"{self.base_url}/audio/speech"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        
        # alloy, echo, fable, onyx, nova, and shimmer
        payload = {
            "model": "tts-1",
            "input": text,
            "voice": voice or "alloy",
        }

        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(url, headers=headers, json=payload)
            resp.raise_for_status()
            return resp.content


class VoiceRegistry:
    def __init__(self) -> None:
        self._providers: dict[str, VoiceProvider] = {
            "mock": MockVoiceProvider(),
            "openai": OpenAIVoiceProvider(),
        }

    def get(self, name: str | None = None) -> VoiceProvider:
        # If no name requested, use openai if available, else mock
        if name is None:
            openai = self._providers["openai"]
            if openai.available():
                return openai
            return self._providers["mock"]

        return self._providers.get(name, self._providers["mock"])

registry = VoiceRegistry()

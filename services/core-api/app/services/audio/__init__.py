"""Audio service — in-memory mic/system audio context for computer control.

Exposes :class:`AudioEngine`, the in-memory audio context described in Module 7
of the full computer-control plan. Importing this package is always safe: no
capture backend or heavy dependency is touched until the engine is started.
"""

from app.services.audio.context import AudioEngine

__all__ = ["AudioEngine"]

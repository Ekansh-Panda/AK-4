"""Vision services package — continuous local screen understanding.

The :class:`VisionEngine` is lazily instantiated via :func:`get_vision_engine`
so the heavy Moondream model is only loaded on first use.
"""

from __future__ import annotations

from app.services.vision.screen import VisionEngine

__all__ = ["VisionEngine", "get_vision_engine"]

_engine: VisionEngine | None = None


def get_vision_engine() -> VisionEngine:
    """Return the process-wide :class:`VisionEngine` (created on first call)."""
    global _engine
    if _engine is None:
        _engine = VisionEngine()
    return _engine

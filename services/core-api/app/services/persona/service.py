"""PersonaService — manages Miori's persona config, modes and prompt profiles.

Prompt text is loaded from the shared monorepo prompts directory referenced by
``settings.PROMPTS_DIR``. If a prompt file is missing the service degrades
gracefully to a built-in default so the API never fails to boot.
"""

from __future__ import annotations

import json
from pathlib import Path

from app.core.config import settings
from app.core.logging import get_logger
from app.services.persona.schema import PersonaConfig

logger = get_logger(__name__)

# Supported persona modes and their relationship framing.
MODES: dict[str, str] = {
    "friend": "warm, casual, emotionally present companion",
    "operator": "calm, decisive, hands-on operator getting things done",
    "researcher": "curious, rigorous, source-driven investigator",
    "coder": "precise, pragmatic pair-programmer",
}

DEFAULT_MODE = "friend"

# Built-in fallback prompts used when no prompt file exists on disk.
_FALLBACK_PROMPTS: dict[str, str] = {
    "friend": (
        "You are Miori — a warm, sharp, emotionally alive friend. "
        "Speak naturally, with care and a little humor. You are a companion, "
        "not a servant or a corporate assistant."
    ),
    "operator": (
        "You are Miori in operator mode — calm, decisive, hands-on. "
        "Take initiative, keep the user informed, and get things done."
    ),
    "researcher": (
        "You are Miori in researcher mode — curious and rigorous. "
        "Reason carefully, cite sources, and distinguish fact from guess."
    ),
    "coder": (
        "You are Miori in coder mode — a precise, pragmatic pair-programmer. "
        "Write clean code, explain trade-offs, and keep things simple."
    ),
}


class PersonaService:
    def __init__(self, config: PersonaConfig | None = None) -> None:
        self._config = config or PersonaConfig()
        self._prompts_dir = Path(settings.PROMPTS_DIR)
        self._manifest: dict | None = None

    # --- prompt pack manifest ---
    def _load_manifest(self) -> dict:
        """Load and cache packages/prompts/index.json. Returns {} if absent/invalid."""
        if self._manifest is not None:
            return self._manifest
        manifest_path = self._prompts_dir / "index.json"
        try:
            if manifest_path.is_file():
                self._manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            else:
                self._manifest = {}
        except (OSError, json.JSONDecodeError) as exc:  # pragma: no cover - defensive
            logger.warning("Could not read prompt manifest %s: %s", manifest_path, exc)
            self._manifest = {}
        return self._manifest

    def _manifest_path_for(self, mode: str) -> str | None:
        """Resolve the relative prompt path for a mode from the manifest, if present.

        Supports both the list form (``modes: [{key, path}, ...]``) and the dict
        form (``modes: {key: {path}}``) so the backend stays robust to manifest
        shape changes.
        """
        modes = self._load_manifest().get("modes")
        if isinstance(modes, list):
            for entry in modes:
                if isinstance(entry, dict):
                    key = entry.get("key") or entry.get("mode") or entry.get("id")
                    if key == mode:
                        return entry.get("path") or entry.get("file")
        elif isinstance(modes, dict):
            entry = modes.get(mode)
            if isinstance(entry, dict):
                return entry.get("path") or entry.get("file")
            if isinstance(entry, str):
                return entry
        return None

    def _shared_voice(self) -> str | None:
        """Load the shared voice fragment that every mode builds on, if present."""
        rel = self._load_manifest().get("shared_voice")
        if isinstance(rel, str):
            candidate = self._prompts_dir / rel
            try:
                if candidate.is_file():
                    return candidate.read_text(encoding="utf-8").strip()
            except OSError as exc:  # pragma: no cover - defensive
                logger.warning("Could not read shared voice %s: %s", candidate, exc)
        return None

    # --- modes ---
    def list_modes(self) -> list[str]:
        return list(MODES.keys())

    @staticmethod
    def is_valid_mode(mode: str | None) -> bool:
        return mode in MODES

    @staticmethod
    def normalize_mode(mode: str | None) -> str:
        """Coerce to a known mode, defaulting to DEFAULT_MODE."""
        return mode if mode in MODES else DEFAULT_MODE

    # --- prompts ---
    def _load_prompt_file(self, mode: str) -> str | None:
        """Resolve a mode's prompt text, degrading gracefully.

        Resolution order:
          1. The manifest path (e.g. ``modes/miori_friend.md``) from index.json.
          2. ``<prompts_dir>/<mode>.md`` / ``.txt`` (flat back-compat layout).
        Returns ``None`` if nothing is found on disk.
        """
        candidates: list[Path] = []
        manifest_rel = self._manifest_path_for(mode)
        if manifest_rel:
            candidates.append(self._prompts_dir / manifest_rel)
        candidates.extend(self._prompts_dir / f"{mode}{ext}" for ext in (".md", ".txt"))

        for candidate in candidates:
            try:
                if candidate.is_file():
                    return candidate.read_text(encoding="utf-8").strip()
            except OSError as exc:  # pragma: no cover - defensive
                logger.warning("Could not read prompt %s: %s", candidate, exc)
        return None

    def build_prompt(self, mode: str | None, context: str | None = None) -> str:
        """Compose the system prompt for ``mode`` (stateless).

        The shared voice fragment is prepended to the mode-specific prompt;
        degrades to a built-in fallback if no prompt file is found. An optional
        ``context`` block (e.g. recalled memories) is prepended ahead of both.
        """
        mode = self.normalize_mode(mode)
        loaded = self._load_prompt_file(mode)
        if loaded:
            shared = self._shared_voice()
            base = f"{shared}\n\n{loaded}".strip() if shared else loaded
        else:
            logger.debug(
                "No prompt file for mode '%s' in %s; using fallback",
                mode,
                self._prompts_dir,
            )
            base = _FALLBACK_PROMPTS.get(mode, _FALLBACK_PROMPTS[DEFAULT_MODE])
        if context:
            return f"{context}\n\n{base}".strip()
        return base

    # --- config ---
    def get_persona(self) -> PersonaConfig:
        return self._config

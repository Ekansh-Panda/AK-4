"""Continuous vision engine — local screen understanding via Moondream.

Module 6 of the full computer-control plan. Replaces the old opt-in vision
model: vision is ON by default whenever ``COMPUTER_USE_ENABLED`` is true and
``COMPUTER_USE_VISION_ENABLED`` has not been disabled.

Design notes
------------
* **Moondream** (local, CPU) is the primary backend and a hard dependency.
* **pytesseract** is an OPTIONAL fallback used only when Moondream's structured
  parse confidence is below ``COMPUTER_USE_VISION_OCR_THRESHOLD`` (0.7).
* A cloud vision LLM (``gpt-4o`` / ``gemini-1.5-pro``) is available as a
  cost-aware escalation path used ONLY when local analysis + OCR both fail.
* Every heavy import (``moondream``, ``pytesseract``, ``pyautogui``, ``mss``,
  ``PIL``) is lazy, so the API still boots on machines without these packages.

All methods are async and run blocking I/O in the default executor.
"""

from __future__ import annotations

import asyncio
import base64
import json
from datetime import datetime, timezone
from io import BytesIO
from pathlib import Path
from typing import Any, Awaitable, Callable

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)

# Confidence below which we fall back to OCR, then to a cloud vision LLM.
_OCR_THRESHOLD = 0.7

# Prompt steering Moondream toward bounded, structured UI output.
_VISION_PROMPT = (
    "Analyze this screenshot of a desktop application UI. "
    "Return ONLY a JSON object of the form "
    '{"elements":[{"label":"button|input|link|text|icon|image|menu|other",'
    '"bounds":[x,y,width,height],"text":"..."}]} '
    "where bounds are integer pixel coordinates [x, y, width, height] "
    "relative to the top-left of the image. "
    "Include only interactive or clearly labelled elements."
)


class VisionEngine:
    """Local, continuous screen-understanding engine backed by Moondream."""

    def __init__(self) -> None:
        self._model: Any | None = None
        self._model_loaded = False
        self._running = False
        self._capture_task: asyncio.Task[None] | None = None
        self._last_elements: list[dict] = []
        self._screencap_dir = Path(settings.COMPUTER_USE_VISION_SCREENCAP_DIR)

    # --- lifecycle / gating ---

    def _ensure_enabled(self) -> None:
        if not settings.COMPUTER_USE_ENABLED:
            raise RuntimeError("Computer use is disabled; vision engine unavailable.")
        if not settings.COMPUTER_USE_VISION_ENABLED:
            raise RuntimeError("Vision is disabled; vision engine unavailable.")

    def is_available(self) -> bool:
        """True when computer use + vision are both enabled."""
        try:
            self._ensure_enabled()
        except RuntimeError:
            return False
        return True

    def _load_model(self) -> None:
        """Lazily load Moondream (no-op if already attempted/failed)."""
        if self._model_loaded:
            return
        self._model_loaded = True
        try:
            import moondream as md  # lazy hard dependency
        except ImportError as exc:  # pragma: no cover - env dependent
            logger.warning("moondream not installed; vision model unavailable: %s", exc)
            self._model = None
            return
        model_id = settings.MOONDREAM_MODEL_PATH or "moondream-2b-int8.mf"
        try:
            self._model = md.vl(model=model_id)
            logger.info("Moondream vision model loaded (%s).", model_id)
        except Exception as exc:  # pragma: no cover - env dependent
            logger.error("Failed to load moondream model %s: %s", model_id, exc)
            self._model = None

    # --- capture ---

    async def capture_screen(self) -> bytes:
        """Take a screenshot, persist it, and return the raw PNG bytes."""
        self._ensure_enabled()
        loop = asyncio.get_event_loop()
        image = await loop.run_in_executor(None, self._capture_sync)

        self._screencap_dir.mkdir(parents=True, exist_ok=True)
        ts = int(datetime.now(timezone.utc).timestamp())
        path = self._screencap_dir / f"screen_{ts}.png"
        await loop.run_in_executor(None, lambda: image.save(str(path), "PNG"))
        logger.info("Screenshot captured: %s", path)

        buf = BytesIO()
        await loop.run_in_executor(None, lambda: image.save(buf, format="PNG"))
        return buf.getvalue()

    def _capture_sync(self):
        """Blocking screenshot using the first available backend."""
        try:
            import pyautogui

            return pyautogui.screenshot()
        except ImportError:
            logger.debug("pyautogui unavailable; trying mss.")

        try:
            import mss
            from PIL import Image

            with mss.mss() as sct:
                monitor = sct.monitors[1] if len(sct.monitors) > 1 else sct.monitors[0]
                shot = sct.grab(monitor)
                return Image.frombytes("RGB", shot.size, shot.bgra, "raw", "BGRX")
        except ImportError:
            logger.debug("mss unavailable; trying PIL.ImageGrab.")

        from PIL import ImageGrab

        image = ImageGrab.grab()
        if image is None:
            raise RuntimeError("No screenshot backend available (pyautogui/mss/PIL).")
        return image

    # --- analysis ---

    async def analyze_screen(self, image_bytes: bytes) -> dict:
        """Analyze raw PNG bytes and return structured element data."""
        self._ensure_enabled()
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(None, self._analyze_sync, image_bytes)
        self._last_elements = result.get("elements", [])
        return result

    def _analyze_sync(self, image_bytes: bytes) -> dict:
        from PIL import Image

        image = Image.open(BytesIO(image_bytes)).convert("RGB")

        if self._model is None:
            self._load_model()
        model = self._model

        raw: str | None = None
        elements: list[dict] = []
        confidence = 0.0

        if model is not None:
            try:
                encoded = model.encode_image(image)
                response = model.query(encoded, _VISION_PROMPT)
                raw = response.get("answer", "") if isinstance(response, dict) else str(response)
                elements, confidence = self._parse_structured(raw, image)
            except Exception as exc:  # pragma: no cover - runtime/env
                logger.error("Moondream query failed (%s); falling back.", exc)
                model = None

        if model is None:
            ocr = self._ocr_fallback(image)
            if not ocr.get("elements"):
                return self._cloud_vision_fallback(image)
            return ocr

        if confidence < _OCR_THRESHOLD:
            logger.info(
                "Moondream confidence %.2f < %.2f; OCR fallback.", confidence, _OCR_THRESHOLD
            )
            ocr = self._ocr_fallback(image)
            if ocr.get("elements"):
                return ocr
            cloud = self._cloud_vision_fallback(image)
            if cloud.get("elements"):
                return cloud

        return {
            "elements": elements,
            "confidence": confidence,
            "backend": "moondream",
            "raw": raw,
        }

    # --- structured parsing ---

    @staticmethod
    def _extract_json(text: str) -> dict | None:
        """Best-effort extraction of the first JSON object from model text."""
        text = text.strip()
        if text.startswith("```"):
            parts = text.split("```")
            if len(parts) >= 2:
                text = parts[1]
                if text.startswith("json"):
                    text = text[4:]
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            start, end = text.find("{"), text.rfind("}")
            if start != -1 and end > start:
                try:
                    return json.loads(text[start : end + 1])
                except json.JSONDecodeError:
                    return None
        return None

    def _parse_structured(self, raw: str, image) -> tuple[list[dict], float]:
        """Parse Moondream text into bounded elements; derive a confidence score."""
        parsed = self._extract_json(raw)
        if not parsed or not isinstance(parsed.get("elements"), list):
            return [], 0.2

        elements: list[dict] = []
        width, height = image.size
        total = len(parsed["elements"])
        valid = 0
        for item in parsed["elements"]:
            if not isinstance(item, dict):
                continue
            bounds = item.get("bounds")
            if not (
                isinstance(bounds, list)
                and len(bounds) == 4
                and all(isinstance(v, (int, float)) for v in bounds)
            ):
                continue
            x, y, w, h = (int(v) for v in bounds)
            if x < 0 or y < 0 or x + w > width or y + h > height or w <= 0 or h <= 0:
                continue
            elements.append(
                {
                    "label": str(item.get("label", "other")),
                    "bounds": [x, y, w, h],
                    "text": str(item.get("text", "")),
                }
            )
            valid += 1

        if not elements:
            return [], 0.2
        confidence = 0.9 if valid == total else 0.6
        return elements, confidence

    # --- OCR fallback ---

    def _ocr_fallback(self, image) -> dict:
        """pytesseract fallback: returns text-block elements with confidences."""
        try:
            import pytesseract
        except ImportError:  # pragma: no cover - optional dep
            logger.warning("pytesseract not installed; OCR fallback unavailable.")
            return {"elements": [], "confidence": 0.0, "backend": "none"}

        try:
            data = pytesseract.image_to_data(
                image, output_type=pytesseract.Output.DICT
            )
        except Exception as exc:  # pragma: no cover - runtime/env
            logger.error("OCR failed: %s", exc)
            return {"elements": [], "confidence": 0.0, "backend": "tesseract-error"}

        elements: list[dict] = []
        confs: list[int] = []
        n = len(data.get("text", []))
        for i in range(n):
            conf = int(data["conf"][i])
            text = (data["text"][i] or "").strip()
            if conf < 0 or not text:
                continue
            x, y = int(data["left"][i]), int(data["top"][i])
            w, h = int(data["width"][i]), int(data["height"][i])
            elements.append({"label": "text", "bounds": [x, y, w, h], "text": text})
            confs.append(conf)

        avg = (sum(confs) / len(confs) / 100.0) if confs else 0.0
        return {"elements": elements, "confidence": avg, "backend": "tesseract"}

    # --- cloud vision LLM escalation (cost-aware, on failure only) ---

    def _cloud_vision_fallback(self, image) -> dict:
        if not settings.COMPUTER_USE_VISION_LLM_ENABLED:
            return {"elements": [], "confidence": 0.0, "backend": "cloud-disabled"}
        try:
            import litellm
        except ImportError:  # pragma: no cover - optional
            logger.warning("litellm unavailable; cloud vision fallback skipped.")
            return {"elements": [], "confidence": 0.0, "backend": "cloud-unavailable"}

        try:
            buf = BytesIO()
            image.save(buf, format="PNG")
            b64 = base64.b64encode(buf.getvalue()).decode("ascii")
            model = settings.COMPUTER_USE_VISION_LLM_MODEL
            resp = litellm.completion(
                model=model,
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": _VISION_PROMPT},
                            {
                                "type": "image_url",
                                "image_url": {"url": f"data:image/png;base64,{b64}"},
                            },
                        ],
                    }
                ],
            )
            text = resp.choices[0].message.content
            parsed = self._extract_json(text or "")
            if parsed and isinstance(parsed.get("elements"), list):
                return {
                    "elements": parsed["elements"],
                    "confidence": 0.95,
                    "backend": f"cloud:{model}",
                }
        except Exception as exc:  # pragma: no cover - runtime/env
            logger.error("Cloud vision LLM failed: %s", exc)
        return {"elements": [], "confidence": 0.0, "backend": "cloud-failed"}

    # --- element access ---

    async def get_elements(self) -> list[dict]:
        """Return the most recent structured elements, capturing if needed."""
        if self._last_elements:
            return list(self._last_elements)
        image = await self.capture_screen()
        result = await self.analyze_screen(image)
        return result.get("elements", [])

    # --- continuous capture ---

    async def start_continuous_capture(
        self, callback: Callable[[dict], Awaitable[None] | None]
    ) -> None:
        """Capture every ``COMPUTER_USE_VISION_INTERVAL_S`` and invoke callback.

        The callback may be sync or async and receives the per-frame analysis
        dict (or ``{"error": ...}`` on capture/analyze failure).
        """
        self._ensure_enabled()
        if self._running:
            logger.warning("Continuous vision capture already running.")
            return
        self._running = True
        self._capture_task = asyncio.create_task(self._capture_loop(callback))
        logger.info(
            "Continuous vision capture started (interval=%ss).",
            settings.COMPUTER_USE_VISION_INTERVAL_S,
        )

    async def _capture_loop(
        self, callback: Callable[[dict], Awaitable[None] | None]
    ) -> None:
        try:
            while self._running:
                try:
                    image = await self.capture_screen()
                    result = await self.analyze_screen(image)
                except Exception as exc:  # pragma: no cover - runtime/env
                    logger.error("Capture/analyze error: %s", exc)
                    await self._invoke(callback, {"error": str(exc)})
                else:
                    await self._invoke(callback, result)
                await asyncio.sleep(settings.COMPUTER_USE_VISION_INTERVAL_S)
        except asyncio.CancelledError:  # pragma: no cover - shutdown path
            pass
        finally:
            self._running = False

    @staticmethod
    async def _invoke(
        callback: Callable[[dict], Awaitable[None] | None], result: dict
    ) -> None:
        if callback is None:
            return
        out = callback(result)
        if asyncio.iscoroutine(out):
            await out

    async def stop_continuous_capture(self) -> None:
        """Stop the continuous capture loop, if running."""
        if not self._running:
            return
        self._running = False
        if self._capture_task is not None:
            self._capture_task.cancel()
            try:
                await self._capture_task
            except asyncio.CancelledError:  # pragma: no cover - shutdown path
                pass
            self._capture_task = None
        logger.info("Continuous vision capture stopped.")

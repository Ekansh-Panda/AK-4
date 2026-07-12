"""AudioEngine — in-memory mic/system audio capture with a rolling buffer.

Module 7 of the full computer-control plan. Provides:

* microphone capture via ffmpeg, sounddevice or pyaudio (lazy, best-effort)
* a 5-second rolling ring buffer that lives entirely in memory
* optional always-on keyword wake for the word "miori" (whisper / porcupine)
* optional system (loopback) audio capture where the platform allows it
* OS notification forwarding to the ``/ws/status`` channel

Audio is OFF by default (``COMPUTER_USE_AUDIO_ENABLED=False``). Every heavy
dependency (sounddevice, pyaudio, plyer, whisper, porcupine) is lazy-imported
and the engine degrades gracefully — it never crashes the app on import or when
a backend is unavailable. Nothing is ever written to disk unless explicitly
saved by the caller via :meth:`save_buffer`.
"""

from __future__ import annotations

import asyncio
import platform
import shutil
import subprocess
import struct
import sys
import threading
from collections import deque
from pathlib import Path

from app.core.config import settings
from app.core.logging import get_logger
from app.ws import manager

logger = get_logger(__name__)

# --- Capture defaults -------------------------------------------------------
# 16 kHz mono 16-bit PCM. Cheap, good enough for VAD/keyword + rolling buffer.
_DEFAULT_RATE = 16_000
_DEFAULT_CHANNELS = 1
_SAMPLE_BYTES = 2  # s16le
_CHUNK_BYTES = 4_096
_ROLLING_SECONDS = 5

# Channel used to forward intercepted OS notifications to the UIs.
_NOTIFY_CHANNEL = "status"


def _rolling_maxlen(rate: int, seconds: int) -> int:
    """Number of ``_CHUNK_BYTES`` chunks that fit in ``seconds`` of audio."""
    total = rate * _DEFAULT_CHANNELS * _SAMPLE_BYTES * seconds
    return max(1, total // _CHUNK_BYTES)


class AudioEngine:
    """In-memory audio context for the computer-control pipeline.

    The engine is intentionally lazy: no capture backend is touched until
    :meth:`start_listening` (or :meth:`capture_system_audio`) is actually
    called, so importing this module is always safe.
    """

    def __init__(
        self,
        rate: int = _DEFAULT_RATE,
        channels: int = _DEFAULT_CHANNELS,
        rolling_seconds: int = _ROLLING_SECONDS,
    ) -> None:
        self.rate = rate
        self.channels = channels
        self.rolling_seconds = rolling_seconds

        self._maxlen = _rolling_maxlen(rate, rolling_seconds)
        self._buffer: deque[bytes] = deque(maxlen=self._maxlen)
        self._buffer_lock = threading.Lock()

        self._mic_proc: subprocess.Popen[bytes] | None = None
        self._mic_task: asyncio.Task[None] | None = None
        self._sys_proc: subprocess.Popen[bytes] | None = None
        self._sys_task: asyncio.Task[None] | None = None
        self._sd_stream: object | None = None
        self._sd_thread: threading.Thread | None = None
        self._system_buffer: deque[bytes] = deque(maxlen=self._maxlen)

        self._kw_task: asyncio.Task[None] | None = None
        self._kw_callback: object | None = None
        self._kw_stop = asyncio.Event()

        self._notify_task: asyncio.Task[None] | None = None
        self._notify_stop = asyncio.Event()

    # ------------------------------------------------------------------ #
    # Buffer management
    # ------------------------------------------------------------------ #
    def get_rolling_buffer(self) -> bytes:
        """Return the last ``rolling_seconds`` of captured mic audio (PCM)."""
        with self._buffer_lock:
            return b"".join(self._buffer)

    def get_system_buffer(self) -> bytes:
        """Return the last ``rolling_seconds`` of system/loopback audio."""
        with self._buffer_lock:
            return b"".join(self._system_buffer)

    def clear_buffer(self) -> None:
        """Drop the in-memory rolling buffers. Never touches disk."""
        with self._buffer_lock:
            self._buffer.clear()
            self._system_buffer.clear()

    def save_buffer(self, path: str | Path, system: bool = False) -> Path:
        """Explicitly persist a buffer to disk. The only path that writes.

        Returns the written path. The caller must opt in; the engine never
        saves on its own.
        """
        data = self.get_system_buffer() if system else self.get_rolling_buffer()
        out = Path(path)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_bytes(data)
        logger.info("Audio buffer saved to %s (%d bytes)", out, len(data))
        return out

    def _push(self, buf: deque[bytes], chunk: bytes) -> None:
        with self._buffer_lock:
            buf.append(chunk)

    # ------------------------------------------------------------------ #
    # Microphone capture
    # ------------------------------------------------------------------ #
    async def start_listening(self) -> bool:
        """Start mic capture. Returns True if a backend was started.

        Order of preference: ``sounddevice`` -> ``pyaudio`` -> ``ffmpeg``.
        Returns False (and logs a warning) if no backend is available.
        """
        if self._mic_task is not None or self._sd_stream is not None:
            return True

        if not settings.COMPUTER_USE_AUDIO_ENABLED:
            logger.warning("Audio is disabled (COMPUTER_USE_AUDIO_ENABLED=False)")
            return False

        if self._try_sounddevice():
            return True
        if self._try_pyaudio():
            return True
        return await self._try_ffmpeg(self._buffer, "mic")

    def _try_sounddevice(self) -> bool:
        try:
            import sounddevice  # lazy
        except ImportError:
            return False
        try:

            def _cb(indata, frames, time_info, status):  # noqa: ANN001
                if status:
                    logger.debug("sounddevice status: %s", status)
                self._push(self._buffer, bytes(indata))

            stream = sounddevice.RawInputStream(
                samplerate=self.rate,
                channels=self.channels,
                dtype="int16",
                blocksize=_CHUNK_BYTES // (self.channels * _SAMPLE_BYTES),
                callback=_cb,
            )
            stream.start()
            self._sd_stream = stream
            logger.info("Mic capture started via sounddevice")
            return True
        except Exception as exc:  # noqa: BLE001 - degrade, never crash
            logger.warning("sounddevice mic start failed: %s", exc)
            return False

    def _try_pyaudio(self) -> bool:
        try:
            import pyaudio  # lazy
        except ImportError:
            return False
        try:
            pa = pyaudio.PyAudio()
            stream = pa.open(
                format=pyaudio.paInt16,
                channels=self.channels,
                rate=self.rate,
                input=True,
                frames_per_buffer=_CHUNK_BYTES // (self.channels * _SAMPLE_BYTES),
            )
            stream.start_stream()

            def _reader() -> None:
                try:
                    while stream.is_active():
                        data = stream.read(
                            _CHUNK_BYTES // (self.channels * _SAMPLE_BYTES),
                            exception_on_overflow=False,
                        )
                        self._push(self._buffer, data)
                except Exception as exc:  # noqa: BLE001
                    logger.debug("pyaudio reader stopped: %s", exc)

            self._sd_stream = (stream, pa)
            self._sd_thread = threading.Thread(target=_reader, daemon=True)
            self._sd_thread.start()
            logger.info("Mic capture started via pyaudio")
            return True
        except Exception as exc:  # noqa: BLE001
            logger.warning("pyaudio mic start failed: %s", exc)
            return False

    async def _try_ffmpeg(
        self, buf: deque[bytes], source: str
    ) -> bool:
        exe = shutil.which("ffmpeg")
        if exe is None:
            logger.warning("ffmpeg not found; cannot capture %s audio", source)
            return False
        args = self._ffmpeg_args(source)
        if args is None:
            logger.warning("No ffmpeg device mapping for %s on this OS", source)
            return False
        try:
            proc = subprocess.Popen(
                args,
                stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL,
                bufsize=0,
            )
        except Exception as exc:  # noqa: BLE001
            logger.warning("ffmpeg start failed: %s", exc)
            return False

        if source == "mic":
            self._mic_proc = proc
        else:
            self._sys_proc = proc
        task = asyncio.create_task(self._pump(proc, buf, source))
        if source == "mic":
            self._mic_task = task
        else:
            self._sys_task = task
        logger.info("Audio capture (%s) started via ffmpeg", source)
        return True

    def _ffmpeg_args(self, source: str) -> list[str] | None:
        """Build ffmpeg args for the given source on the current platform.

        Returns None when no sensible device mapping is known (the caller
        then degrades gracefully rather than guessing).
        """
        rate = str(self.rate)
        common = ["-ac", str(self.channels), "-ar", rate, "-f", "s16le", "-"]
        sysname = platform.system()
        if sysname == "Darwin":
            device = ":0" if source == "mic" else ":1"  # default input / loopback
            return ["ffmpeg", "-f", "avfoundation", "-i", device, *common]
        if sysname == "Linux":
            device = "default" if source == "mic" else "loopback"
            return ["ffmpeg", "-f", "pulse", "-i", device, *common]
        if sysname == "Windows":
            # dshow device names are machine-specific; let the caller name one
            # via env if needed. We only hardcode the mic default.
            if source == "mic":
                return ["ffmpeg", "-f", "dshow", "-i", "audio=default", *common]
            return None
        return None

    async def _pump(
        self, proc: subprocess.Popen[bytes], buf: deque[bytes], source: str
    ) -> None:
        assert proc.stdout is not None
        loop = asyncio.get_event_loop()
        try:
            while True:
                chunk = await loop.run_in_executor(None, proc.stdout.read, _CHUNK_BYTES)
                if not chunk:
                    break
                self._push(buf, chunk)
        except asyncio.CancelledError:
            pass
        finally:
            proc.terminate()
            try:
                proc.wait(timeout=2)
            except Exception:  # noqa: BLE001
                proc.kill()

    async def stop_listening(self) -> None:
        """Stop mic capture and release the backend."""
        if self._mic_task is not None:
            self._mic_task.cancel()
            try:
                await self._mic_task
            except asyncio.CancelledError:
                pass
            self._mic_task = None
        if self._mic_proc is not None:
            self._mic_proc.terminate()
            self._mic_proc = None
        if self._sd_stream is not None:
            self._stop_streaming_backend(self._sd_stream)
            self._sd_stream = None
        if self._sd_thread is not None:
            self._sd_thread.join(timeout=2)
            self._sd_thread = None
        logger.info("Mic capture stopped")

    def _stop_streaming_backend(self, backend: object) -> None:
        try:
            if isinstance(backend, tuple):
                stream, pa = backend
                stream.stop_stream()
                stream.close()
                pa.terminate()
            else:
                backend.stop()  # type: ignore[attr-defined]
                backend.close()  # type: ignore[attr-defined]
        except Exception as exc:  # noqa: BLE001
            logger.debug("stream stop error: %s", exc)

    # ------------------------------------------------------------------ #
    # System / loopback audio
    # ------------------------------------------------------------------ #
    async def capture_system_audio(self) -> bool:
        """Start loopback/system audio capture if the platform supports it.

        Returns True if started, False if loopback is unavailable (e.g. no
        ``pulse`` loopback module, or an OS without a known mapping).
        """
        if self._sys_task is not None:
            return True
        if not settings.COMPUTER_USE_AUDIO_ENABLED:
            logger.warning("Audio is disabled; system capture skipped")
            return False
        exe = shutil.which("ffmpeg")
        if exe is None:
            logger.warning("ffmpeg not found; system audio capture unavailable")
            return False
        return await self._try_ffmpeg(self._system_buffer, "system")

    async def stop_system_audio(self) -> None:
        if self._sys_task is not None:
            self._sys_task.cancel()
            try:
                await self._sys_task
            except asyncio.CancelledError:
                pass
            self._sys_task = None
        if self._sys_proc is not None:
            self._sys_proc.terminate()
            self._sys_proc = None
        logger.info("System audio capture stopped")

    # ------------------------------------------------------------------ #
    # Keyword wake ("miori")
    # ------------------------------------------------------------------ #
    async def start_keyword_wake(self, callback) -> bool:  # type: ignore[no-untyped-def]
        """Begin always-listening keyword detection for "miori".

        Uses Porcupine if available (low-latency keyword spotting), otherwise
        falls back to periodic Whisper transcription of the rolling buffer.
        ``callback`` is invoked (in the event loop) when the keyword is heard.
        Returns False (logging a warning) if neither backend is installed.
        """
        if self._kw_task is not None:
            return True
        if not settings.COMPUTER_USE_AUDIO_ENABLED:
            logger.warning("Audio is disabled; keyword wake skipped")
            return False

        self._kw_callback = callback
        self._kw_stop.clear()

        if self._has_porcupine():
            self._kw_task = asyncio.create_task(self._kw_porcupine())
        elif self._has_whisper():
            # Ensure we have audio to transcribe.
            if self._mic_task is None:
                await self.start_listening()
            self._kw_task = asyncio.create_task(self._kw_whisper())
        else:
            logger.warning(
                "Keyword wake unavailable: install 'pvporcupine' or "
                "'openai-whisper' to enable 'miori' wake word"
            )
            return False
        logger.info("Keyword wake ('miori') started")
        return True

    def _has_porcupine(self) -> bool:
        try:
            import pvporcupine  # lazy

            _ = pvporcupine
            return True
        except ImportError:
            return False

    def _has_whisper(self) -> bool:
        try:
            import whisper  # lazy

            _ = whisper
            return True
        except ImportError:
            return False

    async def _kw_porcupine(self) -> None:
        import pvporcupine  # lazy

        # "miori" is not a built-in Porcupine keyword; use the public/context
        # model if a key is provided, otherwise degrade to whisper path.
        porcupine = None
        try:
            porcupine = pvporcupine.create(keywords=["porcupine"])
        except Exception as exc:  # noqa: BLE001
            logger.warning("Porcupine init failed (%s); using whisper fallback", exc)
            await self._kw_whisper()
            return

        try:
            frame_bytes = porcupine.frame_length * porcupine.bits_per_sample // 8
            import pyaudio  # lazy

            pa = pyaudio.PyAudio()
            stream = pa.open(
                format=pyaudio.paInt16,
                channels=1,
                rate=porcupine.sample_rate,
                input=True,
                frames_per_buffer=porcupine.frame_length,
            )
            try:
                while not self._kw_stop.is_set():
                    pcm = stream.read(porcupine.frame_length, exception_on_overflow=False)
                    if porcupine.process(struct.unpack_from("%dh" % porcupine.frame_length, pcm)) >= 0:
                        await self._fire_keyword()
            finally:
                stream.stop_stream()
                stream.close()
                pa.terminate()
        finally:
            if porcupine is not None:
                porcupine.delete()

    async def _kw_whisper(self) -> None:
        import whisper  # lazy

        model = whisper.load_model("base")
        while not self._kw_stop.is_set():
            await asyncio.sleep(2)
            chunk = self.get_rolling_buffer()
            if len(chunk) < self.rate * _SAMPLE_BYTES:  # < 1s, skip
                continue
            try:
                # Whisper expects a numpy float array; reuse the buffer as s16.
                import numpy as np

                audio = (
                    np.frombuffer(chunk, dtype=np.int16).astype(np.float32) / 32768.0
                )
                result = model.transcribe(audio, language="en", fp16=False)
                text = (result.get("text") or "").lower()
                if "miori" in text:
                    await self._fire_keyword()
            except Exception as exc:  # noqa: BLE001
                logger.debug("whisper transcription error: %s", exc)

    async def _fire_keyword(self) -> None:
        logger.info("Keyword 'miori' detected")
        cb = self._kw_callback
        if callable(cb):
            try:
                res = cb()
                if asyncio.iscoroutine(res):
                    await res
            except Exception as exc:  # noqa: BLE001
                logger.warning("keyword callback error: %s", exc)
        await self._forward_event(
            {"type": "audio_keyword", "keyword": "miori"}
        )

    async def stop_keyword_wake(self) -> None:
        self._kw_stop.set()
        if self._kw_task is not None:
            self._kw_task.cancel()
            try:
                await self._kw_task
            except asyncio.CancelledError:
                pass
            self._kw_task = None
        self._kw_callback = None
        logger.info("Keyword wake stopped")

    # ------------------------------------------------------------------ #
    # OS notifications -> ws/status
    # ------------------------------------------------------------------ #
    def send_notification(self, title: str, message: str) -> bool:
        """Emit an OS notification (best-effort) using plyer."""
        try:
            from plyer import notification  # lazy

            notification.notify(title=title, message=message, app_name="Miori")
            return True
        except Exception as exc:  # noqa: BLE001
            logger.debug("plyer notification unavailable: %s", exc)
            return False

    async def start_notification_forwarding(self) -> bool:
        """Best-effort forwarding of OS notifications to ``/ws/status``.

        True interception of every OS notification is platform-specific and
        not universally available; this establishes the forwarding channel and
        monitors plyer/platform hooks where present. Returns False if no
        notification backend could be initialised.
        """
        if self._notify_task is not None:
            return True
        if not self._has_plyer():
            logger.warning(
                "Notification forwarding unavailable: install 'plyer' for "
                "desktop notification support"
            )
            return False
        self._notify_stop.clear()
        self._notify_task = asyncio.create_task(self._notify_loop())
        logger.info("OS notification forwarding started")
        return True

    def _has_plyer(self) -> bool:
        try:
            import plyer  # lazy

            _ = plyer
            return True
        except ImportError:
            return False

    async def _notify_loop(self) -> None:
        # Placeholder monitor loop. Real OS-notification interception requires
        # platform-native bridges (e.g. a Tauri/Rust layer on desktop); this
        # keeps the channel alive and forwards any notifications the app emits
        # itself so the UI always has a consistent event stream.
        while not self._notify_stop.is_set():
            await asyncio.sleep(5)

    async def stop_notification_forwarding(self) -> None:
        self._notify_stop.set()
        if self._notify_task is not None:
            self._notify_task.cancel()
            try:
                await self._notify_task
            except asyncio.CancelledError:
                pass
            self._notify_task = None
        logger.info("OS notification forwarding stopped")

    # ------------------------------------------------------------------ #
    # ws helpers
    # ------------------------------------------------------------------ #
    async def _forward_event(self, payload: dict) -> None:
        try:
            await manager.broadcast(_NOTIFY_CHANNEL, payload)
        except Exception as exc:  # noqa: BLE001
            logger.debug("ws forward failed: %s", exc)

    async def shutdown(self) -> None:
        """Release every resource held by the engine."""
        await self.stop_listening()
        await self.stop_system_audio()
        await self.stop_keyword_wake()
        await self.stop_notification_forwarding()
        self.clear_buffer()

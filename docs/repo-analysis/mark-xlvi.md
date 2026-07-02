# Mark-XLVI — Repo Analysis

> Engineering due-diligence for Miori Core. Mark-XLVI is one of the project owner's
> private "Mark/Jarvis"-style donor repos and is **not** a public, independently
> documented project. The analysis below is grounded in the donor description given
> in `MISSION.md` ("a Mark/Jarvis-style desktop AI assistant with remote control /
> file transfer / wake-sleep flows"). Where a detail is **inferred** from that
> archetype rather than verified from source, it is labelled `[INFERRED]`. Confirm
> specifics against the actual repo before committing engineering effort.

## 1. What the repo is
Mark-XLVI is a desktop AI assistant in the "Iron Man / J.A.R.V.I.S." lineage — a
voice-and-text personal assistant that runs on the user's machine, listens for a
wake word, executes local actions (open apps, manage files, system control), and
can be driven remotely. It is the most mature iteration of the owner's "Mark" line
(the Roman numeral XLVI = 46 signals a long version history). For Miori Core it is
the closest existing prior-art to the *desktop companion + remote control* half of
the product, so it is the primary harvesting target for remote-control, file-transfer,
and wake/sleep session lifecycle patterns.

## 2. Tech stack `[INFERRED]`
Typical of this assistant archetype; verify against the repo:
- **Language:** Python (assistant core, action handlers).
- **Speech:** wake-word engine (e.g. Porcupine / Vosk / `speech_recognition`), TTS via `pyttsx3` or a cloud TTS.
- **LLM/NLP:** an LLM backend (OpenAI/Gemini/local Ollama) plus intent routing.
- **System control:** `pyautogui` / `os` / `subprocess` / `psutil` for app launching, file ops, screenshots.
- **Remote control / file transfer:** a socket or HTTP/WebSocket channel, possibly a companion mobile/web client; file transfer likely over the same channel or a simple file server.
- **UI:** a lightweight desktop GUI (CustomTkinter / Tkinter / PyQt) or tray-icon driven.
- **Storage:** flat files / SQLite for config, history, and short-term memory.

## 3. Standout features
- **Wake/sleep lifecycle** — idle listening, wake-word activation, active session, return to sleep. This is the single most reusable concept for Miori.
- **Remote control** — drive the desktop assistant from another device.
- **File transfer** — move files between the host machine and a remote client.
- **Local system actuation** — open/close apps, system settings, screenshots, file management.
- **Voice + text dual input** with spoken responses.
- **Conversational memory** of recent turns.

## 4. Strengths
- Real, working prior art for the desktop-companion experience the mission wants.
- Owner-authored, so internal patterns and intent are fully knowable — no license/attribution friction.
- Demonstrates the end-to-end wake → act → respond loop on a real OS.
- Remote-control + file-transfer flows are exactly two of Miori's required modules (`remote`, `files`).

## 5. Limitations / weak points
- **Architecture is likely monolithic** `[INFERRED]` — assistant logic, system control, and UI coupled together; hard to lift cleanly into Miori's modular FastAPI backend.
- **Security of remote control / file transfer is the top risk** `[INFERRED]` — hobby Jarvis projects routinely ship unauthenticated sockets, no transport encryption, and unsandboxed file/system access.
- **Desktop GUI is throwaway** — a Tkinter/CTk "cockpit" conflicts directly with the mission's "no bloated Jarvis cockpit UI / minimal dark elegant" requirement.
- **Tight OS coupling** — `pyautogui`/Windows-specific calls fight the cross-platform (Win/Linux/macOS) constraint.
- **Voice-first assumptions** may not map to Miori's chat-first, friend-like persona.

## 6. What Miori Core should BORROW
- **Wake/sleep session state machine** — model assistant lifecycle states (idle → listening → active → acting → sleeping) as an explicit, observable state machine surfaced over the WebSocket status channel.
- **Remote-control command protocol** — the *shape* of remote commands (issue action, stream result, report status), redesigned around authenticated WebSocket messages.
- **File-transfer flow** — chunked upload/download between host and remote dashboard, with progress events.
- **Local action catalog** — the taxonomy of system actions (open app, file ops, screenshot) as a registry of typed tools.
- **Recent-turn memory** convention as a starting point for short-term memory.

## 7. What Miori Core should NOT borrow
- The desktop GUI / cockpit layout (violates the minimal-UI mandate).
- Any unauthenticated/unencrypted socket or file-transfer code — rebuild on Miori's auth + WS layer.
- OS-specific actuation hardcoding — must be abstracted behind a cross-platform interface.
- Monolithic coupling of NLP + control + UI.
- Voice-first-only interaction defaults.

## 8. Likely integration target inside Miori Core
- Remote command + lifecycle: `services/core-api/app/services/remote/`
- File transfer: `services/core-api/app/services/files/`
- Local action registry (host actuation): `services/core-api/app/services/tools/` (with a host-agent boundary)
- Lifecycle/status broadcasting: `services/core-api/app/ws/`
- Remote control surface UI: `apps/remote-dashboard/` (remote feature) and `apps/desktop/src/features/remote/`

## 9. Implementation risk notes
- **Security is P0-blocking for remote/file features.** Require auth on every remote command, encrypt transport (WSS/TLS), and sandbox/whitelist file paths and actions. Do not port any open-socket pattern verbatim.
- **Cross-platform actuation** needs a clean host-agent abstraction; the donor's OS-specific code is reference, not reusable.
- **Scope creep risk:** the donor's broad "do everything" surface tempts over-building. For v0.1, stub the remote/files interfaces cleanly (mission allows TODO interfaces).

## 10. Priority level
**P1.** Remote + files are required modules and Mark-XLVI is the best prior art for them, but for v0.1 the deliverable is clean interfaces + lifecycle skeleton, not a hardened remote-control plane. Security work pushes full implementation past the v0.1 bar.

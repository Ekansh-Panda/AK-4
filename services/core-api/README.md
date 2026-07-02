# Miori Core API

The backend service for **Miori Core** — a cross-platform personal AI
workstation and desktop companion. It boots fully offline (chat falls back to a
mock provider), uses SQLite by default, and keeps all heavy/optional deps
lazily imported so it still runs on low-end machines ("lite mode").

v1 adds **real model providers** (OpenAI-compatible + Gemini over REST),
**file text ingestion** (text/code/PDF), **memory pinning + filtering +
conversation summaries**, and **active-provider selection** persisted in the DB.

## Stack

- Python 3.11+
- FastAPI + Uvicorn
- Pydantic v2 / pydantic-settings
- SQLAlchemy 2.x (SQLite default)
- WebSockets for streaming chat + status + remote

## Quick start

From the **repo root** (recommended):

```bash
bash scripts/install.sh              # Windows: scripts\install.ps1
bash scripts/run-dev.sh api
```

Or manually inside this directory:

```bash
cd services/core-api

# 1. Create and activate a virtual environment
python -m venv .venv
source .venv/bin/activate           # Windows: .venv\Scripts\activate

# 2. Install dependencies
pip install --upgrade pip wheel
pip install -r requirements-dev.txt   # core + pytest
# pip install -r requirements-optional.txt   # ML/scheduler (optional, large)

# 3. (optional) configure — install.sh copies .env.example automatically
cp .env.example .env

# 4. Run the API
uvicorn app.main:app --reload
```

The API starts on `http://127.0.0.1:8000`. Interactive docs at `/docs`.
On first boot it creates `miori.db` and the `data/uploads/` directory, and logs
the DB path, lite-mode flag, and which providers are configured.

> The runtime deps (`httpx`, `pypdf`) are light and listed in
> `requirements.txt`, but every heavy/optional import is done **lazily inside
> functions**, so the app still imports and runs if they are missing.

## Providers

Three providers ship in the registry:

| Provider | Key(s) | Notes |
| --- | --- | --- |
| `mock` | — | Always available; echoes the last user message. Offline fallback. |
| `openai` | `OPENAI_API_KEY` | OpenAI Chat Completions. Set `OPENAI_BASE_URL` to use OpenRouter (`https://openrouter.ai/api/v1`) or a local OpenAI-compatible server. `OPENAI_MODEL` default `gpt-4o-mini`. |
| `gemini` | `GEMINI_API_KEY` / `GOOGLE_API_KEY` | Google Generative Language API. `GEMINI_MODEL` default `gemini-1.5-flash`. |

The **active** provider is read from the DB at startup (key `active_provider`,
defaulting to `DEFAULT_PROVIDER` then `mock`) and is changeable at runtime:

```bash
# OpenAI
export OPENAI_API_KEY=sk-...
# OpenRouter
export OPENAI_API_KEY=sk-or-... OPENAI_BASE_URL=https://openrouter.ai/api/v1 OPENAI_MODEL=openai/gpt-4o-mini
# Gemini
export GEMINI_API_KEY=...

# pick the active provider at runtime
curl -X PUT localhost:8000/api/providers/active -H 'content-type: application/json' -d '{"name":"openai"}'
```

If the selected provider has no key, chat transparently falls back to `mock` —
it never crashes. `/ws/chat` streams via the active provider's `stream()` and
also falls back to mock on a mid-call provider error.

## File ingestion

`POST /api/files` stores the upload and best-effort extracts text:

- Text/code: `.txt .md .markdown .json .csv .log .py .js .ts .tsx .jsx .html
  .css .yaml .yml .toml .sh .rs .go .java` (decoded UTF-8, `errors="replace"`).
- `.pdf`: extracted via `pypdf` (lazy import); if `pypdf` is absent the file is
  still stored with a note instead of text.
- Other/binary: stored without text.

Uploads over `MAX_UPLOAD_BYTES` (default 25 MB) return **413**. `GET /api/files`
is lightweight (`has_text` boolean, no full text); `GET /api/files/{id}` returns
the full `extracted_text`.

## Memory

`GET /api/memory` supports `?kind=&pinned=&limit=` filters and returns pinned
memories first. `PATCH /api/memory/{id}` toggles `pinned` and/or edits
`content`. ChatService stores a `summary`-kind memory every 10 assistant turns
(best-effort, swallowed on error), using the active provider when available or a
cheap first/last-line heuristic otherwise.

## Lite mode

`LITE_MODE=true` keeps the SQLite substring memory provider and avoids any
heavy/optional code paths. All third-party libs are imported lazily, so the app
boots even without `httpx`/`pypdf` installed.

## Tests

```bash
cd services/core-api
pip install -r requirements-dev.txt   # provides pytest + app deps
pytest                            # offline; no network required
```

Covers: provider registry mock-fallback, memory create/list/filter/pin, and
settings get/set. (Requires `pip install`; the sandbox used to author these has
no package installer.)

## Architecture

```
app/
  main.py            FastAPI app factory, CORS, router wiring, lifespan (DB init)
  core/              config (Pydantic Settings) + logging
  db/                DeclarativeBase, engine, SessionLocal, get_db, init_db
  models/            SQLAlchemy models (UUID ids, timestamps)
  schemas/           Pydantic v2 schemas (from_attributes)
  services/          business logic, all behind clean interfaces
    chat_service.py  orchestrates persona + provider + persistence
    memory/          MemoryProvider ABC + SQLite lite impl + MemoryService
    tools/           Tool ABC + ToolRegistry + example tools (echo/time)
    providers/       ModelProvider ABC + ProviderRegistry + offline MockProvider
    persona/         PersonaService (modes, prompt profiles) + PersonaConfig
    remote/          RemoteSessionService (device registry, sessions)
    tasks/           TaskService (CRUD + scheduler hook stub)
    files/           FileIngestionService (upload + metadata)
  routers/           one router per domain, mounted under /api
  ws/                ConnectionManager + chat/status/remote WebSocket endpoints
```

## REST endpoints (prefix `/api`)

| Method | Path | Purpose |
| --- | --- | --- |
| GET | `/health` | service health (no prefix) |
| POST | `/api/chat` | single-turn chat (mock assistant reply) |
| POST | `/api/chat/sessions` | create a chat session |
| GET | `/api/chat/sessions/{id}/messages` | session history |
| POST | `/api/memory` | add a memory (supports `pinned`) |
| GET | `/api/memory` | list memories (`?kind=&pinned=&limit=`) |
| POST | `/api/memory/search` | search memories |
| GET | `/api/memory/{id}` | get a memory |
| PATCH | `/api/memory/{id}` | edit content / toggle pinned |
| DELETE | `/api/memory/{id}` | delete a memory |
| POST | `/api/files` | upload + extract text (413 if too large) |
| GET | `/api/files` | list files (lightweight, `has_text`) |
| GET | `/api/files/{id}` | file detail incl. `extracted_text` |
| DELETE | `/api/files/{id}` | delete a file |
| GET | `/api/providers` | list providers (availability + active) |
| GET | `/api/providers/models` | models for the active provider |
| GET | `/api/providers/status` | per-provider configured/available |
| PUT | `/api/providers/active` | set + persist active provider |
| GET | `/api/persona` | active persona config + prompt |
| GET | `/api/persona/modes` | list persona modes |
| POST | `/api/persona/mode` | switch mode (friend/operator/researcher/coder) |
| POST/GET | `/api/tasks` | create / list tasks |
| GET/PATCH/DELETE | `/api/tasks/{id}` | task CRUD |
| POST/GET | `/api/remote/devices` | register / list devices |
| POST | `/api/remote/devices/{id}/wake` `/sleep` | device state |
| POST/GET | `/api/remote/...sessions` | remote sessions |
| GET/PUT/DELETE | `/api/settings` | key/value settings |

## WebSocket endpoints

| Path | Purpose |
| --- | --- |
| `/ws/chat` | token-by-token streaming chat (active provider, mock fallback) |
| `/ws/status` | periodic heartbeat for the desktop/remote UIs |
| `/ws/remote` | remote dashboard echo stub |

`/ws/chat` protocol — send `{"message": "...", "session_id"?: "...", "persona_mode"?: "...", "model"?: "..."}`,
receive `{"type":"session"|"token"|"error"|"done", ...}` frames.

## Integration roadmap (donor repos)

- **Mark-XLVI** — real remote control transport + device pairing/auth (`services/remote`, `ws/remote`)
- **Odysseus** — real model providers and vector memory (`services/providers`, `services/memory`)
- **Khoj** — memory ingestion pipeline + task scheduling/APScheduler (`services/files`, `services/tasks`)
- **computer-use** — sandboxed screen/keyboard/file tools (`services/tools`)

These are marked with `TODO(...)` comments at the relevant integration points.

## Caveats

- The mock provider just echoes the last user message; it is the offline fallback when no real provider key is set.
- Memory search is substring matching while `LITE_MODE=true`.
- New columns (`files.extracted_text`, `memories.pinned`) are backfilled on an existing SQLite DB by a tiny additive step in `init_db` (no Alembic).
- Conversation summaries fire every 10 assistant turns, best-effort; failures are swallowed and never break a chat turn.
- Remote sessions are in-memory (lost on restart); devices persist in the DB.
- No auth yet — intended for local/dev use.

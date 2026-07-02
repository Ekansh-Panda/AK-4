# Miori Core — Roadmap & Backlog

> The schedule of record for Miori Core. The **map** (capability → donor repo → module) lives in
> [docs/feature-matrix.md](docs/feature-matrix.md); this file is the **plan** (what gets built when,
> and what is mocked vs implemented).
>
> Related: [System Overview](docs/architecture/system-overview.md) · [Data Model](docs/architecture/data-model.md) · [API Surface](docs/architecture/api-surface.md) · [Visual Direction](docs/ui-spec/visual-inspirations.md) · [Overnight Build Plan](docs/overnight-plan/build-plan.md)

Guiding principle ([MISSION.md](MISSION.md)): **a working v0.1 foundation, not a finished AI.**
Miori must feel like a *friend, not a cockpit*, and stay usable on low-end machines.

---

## v0.1 — Tonight (Foundation / scaffold)

The scaffold delivers:

- [x] Monorepo structure (`apps/`, `services/`, `packages/`)
- [x] Desktop app shell — Tauri + React + TS + Tailwind + shadcn/ui (`apps/desktop/`)
- [x] All 8 pages render: Chat, Files, Memory, Projects, Research, Tasks, Remote, Settings (`apps/desktop/src/features/*`)
- [x] Layout shell + sidebar + status bar (`apps/desktop/src/components/layout/`)
- [x] Presence orb stub (cheap CSS, no WebGL) (`apps/desktop/src/components/`)
- [x] Remote dashboard shell (`apps/remote-dashboard/`)
- [x] FastAPI app boots with REST `/api/*` + WS `/ws/*` registered (`services/core-api/`)
- [x] SQLAlchemy models for all 8 tables + SQLite engine/session (`services/core-api/app/models/*`, `db/*`)
- [x] Service-layer skeletons: memory, providers, tools, persona, remote, tasks, files (`services/core-api/app/services/*`)
- [x] Persona system skeleton with `friend`/`operator`/`researcher`/`coder` modes + prompt profiles (`packages/prompts/`)
- [x] Provider abstraction with lite `echo`/mock default (`services/core-api/app/services/providers/`)
- [x] Memory abstraction (SQLite text store, no embeddings) (`services/core-api/app/services/memory/`)
- [x] Tool registry contract (`services/core-api/app/services/tools/`)
- [x] Chat streaming over `/ws/chat`, messages persisted (`services/core-api/app/ws/chat.py`)
- [x] Status heartbeat over `/ws/status`
- [x] `LITE_MODE` + `REMOTE_ENABLED` flags + `.env.example` (`services/core-api/app/core/config.py`)
- [x] Shared design tokens + UI primitives (`packages/ui/`) + shared types (`packages/types/`)
- [x] Repo analysis docs (`docs/repo-analysis/` — separate job)
- [x] Integration feature matrix + architecture/UI/plan docs (`docs/`)
- [x] README with run instructions for backend + both frontends

---

## v0.2 — Integration phase (wire real backends)

Flip the mocks into real behavior, one abstraction at a time. **v1 landed the
provider + file-ingestion slices and wired both frontends to the backend; the
remaining items (semantic memory, real remote transport, status fan-out) carry
forward.**

- [x] **Real model providers** behind the provider interface — OpenAI / OpenAI-compatible (OpenRouter, local) + Gemini (`services/core-api/app/services/providers/`)
  - [x] Lazy-import each provider SDK (only when selected)
  - [x] API-key config via `settings` table (`active_provider`) + `.env`
  - [x] Real token streaming through `/ws/chat` (mock fallback on missing key / mid-call error)
- [x] **Memory retrieval** — upgrade from keyword to semantic recall (`services/core-api/app/services/memory/`)
  - [x] Memory pinning + `?kind=&pinned=&limit=` filtering + conversation summaries (every 10 turns)
  - [x] Optional embedding provider (lazy, off in lite mode)
  - [x] Optional vector index (no mandatory vector DB)
  - [x] `recall()` wired into the chat orchestration loop
- [ ] **Remote transport** — real device pairing + relay (`services/core-api/app/services/remote/`, `ws/remote.py`)
  - [ ] Pairing secrets / auth tokens on `devices` (extend `models/device.py`)
  - [ ] Live presence over `/ws/remote`; dashboard reaches paired devices
- [x] **File ingestion** — text extraction (text/code/PDF) on upload (`services/core-api/app/services/files/`)
  - [x] `POST /api/files` extracts text (413 over `MAX_UPLOAD_BYTES`); `GET /api/files/{id}` returns `extracted_text`
  - [x] Chunk → index pipeline; searchable content feeding memory/research
- [ ] **Persona depth** — mode-specific tuned prompts + memory-aware tone (`packages/prompts/`)
- [ ] **Status bus** — real event fan-out (provider health, task, device) over `/ws/status`
- [ ] **Presence orb** reactive to real chat/voice state
- [x] **Frontends wired to the backend** — desktop + remote talk to `core-api` over REST + WS (mock fallback when offline)
- [x] **Setup docs + dev scripts** — `docs/setup/INSTALLATION.md`, `scripts/env-validate.{sh,ps1}`, `scripts/db-init.{sh,ps1}`

---

## v0.3 — Advanced automation

- [x] **Computer-use** — sandboxed actions (screenshot/click/type/shell), safety gating, opt-in only (`services/core-api/app/services/tools/`, `ws/remote.py`)
- [ ] **Voice pipeline** — STT/TTS, push-to-talk, amplitude-reactive orb (`services/providers/` voice, `apps/desktop/src/features/chat/`)
- [x] **Multi-agent orchestration** — agent loop + sub-agent delegation over the tool registry
- [x] **Task scheduler** — APScheduler recurring/cron jobs; add `cron`/`next_run` to `models/task.py`
- [ ] **Projects & Research** pages graduate from placeholders to real workspaces
- [ ] **Packaging** — Tauri installers for Windows/Linux/macOS; backend bundling; first-run setup
- [ ] **3D presence orb** as an opt-in, setting-gated enhancement (still off by default for low-end)

---

## Low-end optimization rules (apply to every version)

- [ ] Heavy deps are **lazy-imported** inside the function that needs them — never at module load
- [ ] **SQLite is the default**; no external DB server required to run Miori
- [ ] **`LITE_MODE=True` by default** — app is fully usable with **zero API keys**
- [ ] **No mandatory vector DB** — semantic memory is an optional upgrade
- [ ] Feature flags (`LITE_MODE`, `REMOTE_ENABLED`, per-provider) gate all cost
- [ ] Frontends stay thin; no always-on 3D/animation in the baseline; respect `prefers-reduced-motion`
- [ ] Everything **degrades gracefully** — missing keys/prompts/remote never crash boot

---

## Mocked vs implemented (as of v0.2)

### Real / implemented
- [x] Monorepo + desktop shell + remote dashboard shell, both wired to the backend
- [x] FastAPI app, REST + WS routes registered
- [x] SQLite + all 8 tables, CRUD **persistence** (sessions, messages, memories, files, tasks, settings, devices)
- [x] `GET /api/health`
- [x] Service-layer interfaces + lite default implementations
- [x] `LITE_MODE` / `REMOTE_ENABLED` config
- [x] **Real model providers** — OpenAI / OpenAI-compatible (OpenRouter, local) + Gemini, lazy-imported, with mock fallback
- [x] **Active-provider selection** persisted in the DB + `PUT /api/providers/active`
- [x] Real token streaming over `/ws/chat`
- [x] **File text ingestion** (text/code/PDF) on upload
- [x] Memory **pinning + filtering + conversation summaries**
- [x] Setup docs (`docs/setup/INSTALLATION.md`) + dev scripts (`env-validate`, `db-init`)
- [x] **Semantic memory** (ChromaDB + SentenceTransformers) + chat recall integration
- [x] **File indexing** (chunking + ingestion pipeline)
- [x] **Task scheduler** (APScheduler + background tasks)
- [x] **Computer-use tools** (PyAutoGUI + sandbox + audit log)
- [x] **Agent tool-calling loop** (LLM invokes tools iteratively)

### Still mocked / lite (to be made real in v0.3)
- [ ] Persona = **static friend-first prompt** (no mode tuning)
- [ ] Remote = **mock device presence**, no real pairing/transport
- [ ] Status bus = **heartbeat + canned events**
- [ ] Voice = **mock provider endpoints**

### Deferred (interface/TODO only)
- [ ] packaging → v0.3

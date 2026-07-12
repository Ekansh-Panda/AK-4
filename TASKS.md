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
  - [x] Pairing secrets / auth tokens on `devices` (extend `models/device.py`)
  - [x] Live presence over `/ws/remote`; dashboard reaches paired devices
- [x] **File ingestion** — text extraction (text/code/PDF) on upload (`services/core-api/app/services/files/`)
  - [x] `POST /api/files` extracts text (413 over `MAX_UPLOAD_BYTES`); `GET /api/files/{id}` returns `extracted_text`
  - [x] Chunk → index pipeline; searchable content feeding memory/research
  - [x] `GET /api/files/search` (`?q=&k=`) — semantic or substring over `file_chunks`
- [x] **Persona depth** — mode-specific tuned prompts + memory-aware tone + self-evolving persona (every 10 turns / 24h) (`packages/prompts/`, `services/core-api/app/services/persona/`)
- [x] **Status bus** — real event fan-out (provider health, task due, research, tool_approval, presence-orb state) over `/ws/status`
- [x] **Presence orb** reactive to real chat/voice/agent state (driven by `/ws/status` events)
- [x] **Projects & Research** — real workspaces (`/api/projects` CRUD linking sessions/tasks/files; `/api/research` background agent persisting findings + a `kind="research"` memory row)
- [x] **Auth (single-user)** — `miori-local` user created on first boot, `default_user_id` in settings; `MIORI_API_TOKEN` still enforced when set
- [x] **Tools / agent approval** — `requires_approval` tools pause the ReAct loop and broadcast `tool_approval` over `/ws/status`; `POST /api/tools/approve|reject`; `agent_mode` setting gates the loop
- [x] **Provider reachability** — `GET /api/providers/status` (with `reachable`) + `GET /api/providers/ping` (cached ~60s TTL)
- [x] **Frontends wired to the backend** — desktop + remote talk to `core-api` over REST + WS; plans viewer, computer-use settings, mock data removed, honest empty states, degraded connection handling
- [x] **Setup docs + dev scripts** — `docs/setup/INSTALLATION.md`, `scripts/env-validate.{sh,ps1}`, `scripts/db-init.{sh,ps1}`

---

## v0.3 — Advanced automation

- [x] **Computer-use** — full agentic tools (shell, filesystem, browser, system), planner/executor, trust levels, audit/undo logs, continuous vision, audio context (`services/core-api/app/services/tools/`, `services/core-api/app/services/planner/`, `services/core-api/app/services/vision/`, `services/core-api/app/services/audio/`)
  - [x] Computer-use **frame streaming** over `/ws/remote`
  - [x] **429-aware provider retry** — exponential backoff (1s, 2s, 4s), silent cross-provider fallback, mock as last resort, applies to both REST and WS paths (`services/core-api/app/services/providers/base.py`, `registry.py`)
  - [x] **Continuous vision** — moondream primary backend with pytesseract OCR fallback and cloud LLM escalation
  - [x] **Audio context** — rolling mic buffer, keyword wake, notification forwarding
- [x] **Voice pipeline** — STT/TTS, push-to-talk, amplitude-reactive orb (`services/providers/` voice, `apps/desktop/src/features/chat/`)
- [x] **Multi-agent orchestration** — agent loop + sub-agent delegation over the tool registry
- [x] **Task scheduler** — APScheduler recurring/cron jobs; add `cron`/`next_run` to `models/task.py`
- [x] **Projects & Research** pages graduate from placeholders to real workspaces
- [ ] **Remote (WAN) pairing + relay** — real transport beyond LAN; pairing secrets (`models/device.py`)
- [ ] **Multi-user** — account provisioning beyond the single `miori-local` identity
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

## Mocked vs implemented (as of v1.2.0)

### Real / implemented
- [x] Monorepo + desktop shell + remote dashboard shell, both wired to the backend
- [x] FastAPI app, REST + WS routes registered
- [x] SQLite + all tables, CRUD **persistence** (sessions, messages, memories, files, tasks, settings, devices, plans, plan_steps)
- [x] `GET /api/health`
- [x] Service-layer interfaces + lite default implementations
- [x] `LITE_MODE` / `REMOTE_ENABLED` config
- [x] **Real model providers** — 10 providers (OpenAI, Gemini, Groq, Mistral, SambaNova, OpenRouter, HuggingFace, Cohere, Cloudflare, Mock), lazy-imported, with 429-aware retry + cross-provider fallback
- [x] **Active-provider selection** persisted in the DB + `PUT /api/providers/active`
- [x] Real token streaming over `/ws/chat`
- [x] **File text ingestion** (text/code/PDF) on upload
- [x] Memory **pinning + filtering + conversation summaries + persona evolution**
- [x] Setup docs (`docs/setup/INSTALLATION.md`) + dev scripts (`env-validate`, `db-init`)
- [x] **Semantic memory** (ChromaDB + SentenceTransformers) + chat recall integration
- [x] **File indexing** (chunking + ingestion pipeline) + `GET /api/files/search`
- [x] **Task scheduler** (APScheduler + background tasks)
- [x] **Computer-use tools** (unrestricted shell, filesystem, browser, system tools; trust levels; audit/undo logs)
- [x] **Agent tool-calling loop** (LLM invokes tools iteratively)
- [x] **Execution plans** (PlannerService + ExecutorService with parallel batches, replan, double-verify)
- [x] **Continuous vision** (moondream + pytesseract OCR fallback)
- [x] **Audio context** (rolling mic buffer, keyword wake, notification forwarding)
- [x] **Tools / agent approval** (`tool_approval` pause + broadcast, `POST /api/tools/approve|reject`, `agent_mode` gate)
- [x] **Plan approval** (`step_approval_needed` broadcast, `POST /api/plans/{id}/steps/{step_id}/approve`)
- [x] **Voice** (OpenAI Whisper STT + TTS, mock fallback; desktop push-to-talk)
- [x] **Projects** (`/api/projects` CRUD, linked sessions/tasks/files; `project_id` FK)
- [x] **Research** (background agent, persisted `research` row + `kind="research"` memory)
- [x] **WebSocket status bus** (real fan-out: plan/task/research/tool_approval/step_approval/provider reachability/presence-orb)
- [x] **Presence orb** reactive to `/ws/status` state
- [x] **Auth (single-user)** (`miori-local` user on first boot, `default_user_id` in settings)
- [x] **Provider reachability** (`/api/providers/status` `reachable` + cached `/api/providers/ping`)

### Still mocked / lite (intentionally, per constraints)
- [ ] Remote = **LAN-only / mock device presence**, no real WAN pairing/transport, no pairing secrets
- [ ] Multi-user = **single `miori-local` identity** only

### Deferred (interface/TODO only)
- [ ] multi-user accounts
- [ ] packaging → v0.3

---

## v1.2 — Full Computer Control

- [x] Trust levels + settings API (`manual`, `auto-shell`, `trusted`, `god`)
- [x] Plan/step models + CRUD + WS lifecycle events
- [x] PlannerService (LLM decomposition, parallel sub-plans, double-verification)
- [x] ExecutorService (parallel batches, replan, LLM-retry, timeout, approval)
- [x] Unrestricted agentic tools (shell, fs, browser, system)
- [x] Hardened `computer_use.py` (no mock fallback, pyautogui hard dep, list-of-args shell)
- [x] Continuous vision engine (moondream + pytesseract fallback)
- [x] Audio engine (rolling buffer, keyword wake, notification forwarding)
- [x] Provider 429 retry wrapper + cross-provider fallback
- [x] PersonaEvolutionService (every 10 turns / 24h, `persona:evolution` memory block)
- [x] Frontend: Plans viewer + ComputerUseSettings + mock data removed
- [x] Tests: plan CRUD, auth, WS broadcasts

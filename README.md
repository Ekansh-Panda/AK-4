<div align="center">

# Miori Core

![Local](https://img.shields.io/badge/runtime-local-green)
![Offline](https://img.shields.io/badge/offline--capable-mock--provider-blue)
![Monorepo](https://img.shields.io/badge/monorepo-pnpm%20%2B%20Python-orange)
![FastAPI](https://img.shields.io/badge/API-FastAPI%20%2B%20Uvicorn-009688)
![Tauri%20v2](https://img.shields.io/badge/desktop-Tauri%20v2-FFC131)
![React](https://img.shields.io/badge/frontend-React%20%2B%20TS-61DAFB)
![v1.2.0](https://img.shields.io/badge/version-1.2.0-brightgreen)

**A cross-platform personal AI companion — desktop, remote, and always present.**

*Warm. Sharp. Present. A friend, not a servant.*

</div>

---

Miori Core is the foundation of **Miori** — a personal AI you live alongside: a desktop companion you talk to, a workspace you think in, and a remote presence you reach from your phone. Built as a clean, modular monorepo with a real, wired-up spine. The deeper intelligence (semantic memory, computer-use, voice, multi-agent) lands behind clean interfaces and feature flags — not as fluff, but as lazy-loaded, opt-in capability.

> **Status:** v1.2.0 — Full computer control. The desktop app, remote dashboard, and FastAPI backend are wired over REST + WebSocket with **real model providers** (OpenAI, Gemini, Groq, Mistral, SambaNova, OpenRouter, HuggingFace, Cohere, Cloudflare + LiteLLM orchestrator with 429-aware retry), **SQLite persistence**, **file text ingestion**, **streaming chat**, **ReAct agent loop with human approval**, **execution plans** with planner/executor, **unrestricted agentic tools** (shell, filesystem, browser, system), **continuous vision** (moondream + pytesseract), **audio context**, **self-evolving persona**, **background research**, **projects**, **tasks**, and **device remote control**. Frontends render honest empty states when the backend is unreachable. Runs in **lite mode** by default so it stays usable on low-end machines.

---

## Features

### Chat & Persona
- **Token streaming** over WebSocket (`/ws/chat`) with cancel/regenerate
- **Persona modes**: `friend`, `operator`, `researcher`, `coder` — warm, context-aware system prompts from `packages/prompts/`
- **Offline mock fallback**: echoes your last message with zero keys; frontends degrade gracefully when the backend is unreachable

### Memory
- **CRUD** memory entries with namespaced storage (`facts`, `preferences`, `projects`, `research`)
- **Pinning** and filtering by namespace
- **Fact capture** during chat (mocked in lite mode, real in production)
- **Optional semantic/vector search** via ChromaDB / sentence-transformers, gated by `SEMANTIC_MEMORY_ENABLED`; falls back to SQLite substring search in lite mode

### File Intelligence
- **Upload** multipart files (images, PDFs, docs) up to 25 MB
- **Text extraction** and chunking pipeline (Khoj-inspired)
- **Search** over ingested content — semantic when embeddings are enabled, substring in lite mode
- Async ingestion status: `uploaded` → `ingesting` → `ingested` / `failed`

### Agent & Tools
- **ReAct loop**: tool-calling agent with streaming responses
- **Human approval** for dangerous tools (`requires_approval=True`) — paused via `/ws/status` `tool_approval` event, resolved through `POST /api/tools/approve` or `/reject`
- **Execution plans**: decompose goals into executable steps; parallel sub-plans; step-level approval; replan on failure; double-verification for critical actions
- **Unrestricted agentic tools**:
  - `shell`: execute commands as `list[str]` (no `shell=True`)
  - `fs_write`, `fs_read`, `fs_list`, `fs_delete` with in-memory undo log
  - `browser`: Playwright persistent context (goto, click, type, scroll, screenshot, pdf, evaluate)
  - `install`, `process`, `service`, `clipboard`, `notify`, `git`, `docker`
- **Computer-use** (unrestricted, trust-gated): screenshot, click, type, keypress, scroll — pyautogui is a hard dependency when enabled
- **Trust levels**: `manual`, `auto-shell`, `trusted`, `god` — control approval speed, not capability
- **Arm/disarm audit log**: explicit `arm` / `disarm` endpoints with full audit trail

### Research Agent
- Background LLM-powered deep-dive research
- Persisted findings with cited sources
- Live **WebSocket broadcast** of research status (`/ws/status`)
- Auto-persists a `memories` row with `kind="research"`

### Projects
- **CRUD** project workspaces linking sessions, tasks, and files
- Project briefs for AI context
- Status lifecycle: `active` / `archived` / `completed`

### Tasks & Scheduling
- Full **task CRUD** with status lifecycle: `pending` / `in_progress` / `done` / `cancelled`
- **APScheduler** hook for recurring and scheduled jobs (Khoj patterns)
- Due-date tracking and background scheduler gated by `SCHEDULER_ENABLED`

### Audio
- **STT** via OpenAI Whisper (lazy-loaded) with mock fallback
- **TTS** via OpenAI TTS (lazy-loaded) with mock fallback
- Desktop push-to-talk: `MediaRecorder` → `POST /api/audio/transcribe`

### Remote Control
- **Device pairing** with bearer auth and hash-based secrets
- **Wake / sleep** commands for paired devices
- **Presence** state: `online` / `offline` / `sleeping`
- **WebSocket relay** for real-time remote presence and control frames

### Multi-Provider
- **10 providers** out of the box: Mock, OpenAI, Gemini, Groq, Mistral, SambaNova, OpenRouter, HuggingFace, Cohere, Cloudflare Workers AI
- **LiteLLM orchestrator** with cross-provider failover (opt-in via `ORCHESTRATOR_ENABLED`)
- **429-aware retry** with exponential backoff and silent fallback across providers (applies to both REST and WS paths)
- Lazy-import per provider — no heavy SDK cost at boot
- Transparent fallback to `mock` when a configured provider is unreachable

### Frontends
- **Tauri desktop** (v2): native window shell, tabbed workspace, presence orb — runs on Windows, Linux, macOS
- **React remote dashboard**: mobile-first browser app reachable from your phone on the LAN
- **Honest empty states**: frontends show "not connected / auth required" instead of mock data when the backend is unreachable

### Observability
- **Structured logging** throughout the backend
- **Health endpoint** (`GET /api/health`) with version, lite mode flag, and remote enabled flag
- **Provider ping** (`GET /api/providers/ping`) with ~60s TTL reachability cache
- Live **WebSocket status bus** (`/ws/status`) fanning out heartbeat, provider state, task events, research status, tool approvals, plan lifecycle events, and presence-orb state

### Continuous Vision
- **Moondream** local screen understanding (CPU-friendly, runs on-device)
- **pytesseract OCR** fallback when Moondream confidence is low
- Continuous 2s capture cadence during plan execution
- Optional cloud vision LLM escalation (gpt-4o / gemini-1.5-pro) for complex UI understanding

### Audio Context
- **Rolling 5s mic buffer** in memory (never persisted unless saved)
- **System audio** loopback capture where available
- **Keyword wake** always-listening for "miori" (Porcupine/Whisper)
- **OS notification** forwarding to `/ws/status`

### Self-Evolving Persona
- Distills user preferences, corrections, and style signals every 10 turns or 24 hours
- Stores compact `persona:evolution` memory block
- Appends learned preferences to the next system prompt automatically

---

## Architecture

Miori Core is a **clean modular monorepo** — not a merge of donor repos. All intelligence lives in `services/core-api`; frontends are thin shells.

```
┌─────────────────────────────────────────────────────────────┐
│                     services/core-api                        │
│              FastAPI · REST /api · WS /ws                     │
│                                                              │
│  routers/  →  services/  →  models/  →  db (SQLite)         │
│    chat       memory       user                                │
│    memory     providers    session                             │
│    plans      persona      message                            │
│    providers  planner      memory                             │
│    persona    executor     file                               │
│    remote     tools        task                               │
│    tasks      vision       device                             │
│    settings   audio        project                            │
│                          research                             │
└─────────────────────────────────────────────────────────────┘
         ▲                              ▲
         │ REST /api  +  WS /ws         │
         │                              │
┌────────┴──────────┐          ┌────────┴──────────┐
│   apps/desktop     │          │ apps/remote-dashboard │
│ Tauri v2 · React   │          │   React · TypeScript  │
│                    │          │                      │
│  ┌──────────────┐  │          │  Mobile-first web UI │
│  │ Chat · Files │  │          │  · reach from phone  │
│  │ Memory · ... │  │          │                      │
│  └──────────────┘  │          └──────────────────────┘
└────────────────────┘
         ▲
         │ shared tokens, types, prompts
         │
┌────────┴────────────────────────────────────────┐
│  packages/                                      │
│  ui/         Shared design system (Tailwind)     │
│  types/      TypeScript contracts (API mirror)   │
│  prompts/    Persona prompt packs                │
└─────────────────────────────────────────────────┘
```

**Rule:** `routers/ws → services → models/db`. Services never import routers; UI never imports service internals. All communication is HTTP or WebSocket.

Full details: [`docs/architecture/system-overview.md`](./docs/architecture/system-overview.md)

---

## Quick Start

### Prerequisites

| Tool | Version | Required for |
| --- | --- | --- |
| Python | 3.11+ | Backend |
| Node.js | 18+ | Frontends |
| pnpm | 9+ | Frontends |
| Rust + Cargo | stable | Native desktop build only |
| Git | any | Clone |

> The web UIs and backend run without the Rust toolchain. Rust is only needed for `tauri dev` / `tauri build`.

### One-Command Bootstrap

```bash
# 1) Clone and install
git clone <repo-url> miori-core
cd miori-core
bash scripts/install.sh          # Windows: scripts\install.ps1

# 2) Validate environment
bash scripts/env-validate.sh     # Windows: scripts\env-validate.ps1

# 3) Run everything
bash scripts/run-dev.sh all       # api + desktop + remote together
```

### Run Individual Pieces

```bash
bash scripts/run-dev.sh api       # FastAPI on http://127.0.0.1:8000 (docs at /docs)
bash scripts/run-dev.sh desktop   # Desktop web UI on http://localhost:1420
bash scripts/run-dev.sh remote    # Remote dashboard on http://localhost:5174
```

Or manually:

```bash
# Backend
cd services/core-api
source .venv/bin/activate
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000

# Desktop (web mode — no Rust)
pnpm --filter @miori/desktop dev

# Desktop (native — requires Tauri prerequisites)
pnpm --filter @miori/desktop tauri dev

# Remote dashboard
pnpm --filter @miori/remote-dashboard dev
```

### Database

The SQLite database (`miori.db`) and uploads directory are created automatically on first backend boot. To initialize without starting the server:

```bash
bash scripts/db-init.sh           # Windows: scripts\db-init.ps1
```

Full setup guide per OS: [`docs/setup/INSTALLATION.md`](./docs/setup/INSTALLATION.md)

---

## Configuration

### Environment Variables

Miori reads config from `.env` files. The backend `Settings` class reads **bare, un-prefixed** names (case-insensitive). Frontends read `VITE_*` variables.

**Backend** (`services/core-api/.env` — copy from `.env.example`):

| Variable | Default | Purpose |
| --- | --- | --- |
| `APP_NAME` | `Miori Core` | Display name |
| `APP_VERSION` | `1.2.0` | Reported version |
| `HOST` | `127.0.0.1` | API bind address |
| `PORT` | `8000` | API port |
| `DATABASE_URL` | `sqlite:///./miori.db` | SQLAlchemy URL (SQLite default) |
| `CORS_ORIGINS` | dev origins | Comma-separated allowed origins |
| `UPLOAD_DIR` | `./data/uploads` | File storage path |
| `MAX_UPLOAD_BYTES` | `26214400` | 25 MB upload limit |
| `PROMPTS_DIR` | `../../packages/prompts` | Persona prompt packs |
| `DEFAULT_PROVIDER` | `mock` | Active provider on first boot |

**Provider keys** (`services/core-api/.env`):

| Variable | Purpose |
| --- | --- |
| `OPENAI_API_KEY` / `OPENAI_API_KEYS` | OpenAI / OpenRouter / local compatible |
| `OPENAI_BASE_URL` | Override for OpenRouter / Ollama / LM Studio |
| `OPENAI_MODEL` | Default OpenAI model |
| `GEMINI_API_KEY` / `GOOGLE_API_KEY` | Google Gemini |
| `GEMINI_MODEL` | Default Gemini model |
| `GROQ_API_KEY` | Groq |
| `MISTRAL_API_KEY` | Mistral AI |
| `SAMBANOVA_API_KEY` | SambaNova |
| `OPENROUTER_API_KEY` | OpenRouter |
| `HUGGINGFACE_API_KEY` | HuggingFace |
| `COHERE_API_KEY` | Cohere |
| `CLOUDFLARE_API_KEY` / `CLOUDFLARE_ACCOUNT_ID` | Cloudflare Workers AI |

**Frontend** (root `.env`):

| Variable | Default | Purpose |
| --- | --- | --- |
| `VITE_MIORI_API` | `http://localhost:8000/api` | Desktop REST base URL |
| `VITE_MIORI_WS` | `ws://localhost:8000/ws/chat` | Desktop chat WebSocket |

### Feature Flags

| Variable | Default | Effect |
| --- | --- | --- |
| `LITE_MODE` | `true` | Disables vector DB, heavy embeddings, and remote pairing. Uses raw SQLite text search. |
| `REMOTE_ENABLED` | `true` | Exposes dashboard and pairing routes to the LAN |
| `COMPUTER_USE_ENABLED` | `false` | Allows full computer control when armed |
| `COMPUTER_USE_SHELL_ENABLED` | `false` | Allows shell command execution |
| `COMPUTER_USE_TRUST_LEVEL` | `manual` | Approval speed: `manual`, `auto-shell`, `trusted`, `god` |
| `COMPUTER_USE_MAX_STEPS` | `50` | Max steps per execution plan |
| `COMPUTER_USE_PLAN_TIMEOUT_S` | `600` | Plan timeout in seconds |
| `COMPUTER_USE_VISION_ENABLED` | `true` | Moondream continuous vision (on by default when computer-use is enabled) |
| `COMPUTER_USE_AUDIO_ENABLED` | `false` | Mic/system audio + keyword wake |
| `COMPUTER_USE_DOUBLE_VERIFY` | `true` | Secondary-model verification for critical actions |
| `COMPUTER_USE_BROWSER_ENABLED` | `false` | Playwright browser automation |
| `SEMANTIC_MEMORY_ENABLED` | `false` | Enables embedding + ChromaDB vector search for memory |
| `SCHEDULER_ENABLED` | `true` | Spins up APScheduler background task system |
| `MIORI_API_TOKEN` | _(empty)_ | When set, enforces Bearer token auth on REST API |
| `ORCHESTRATOR_ENABLED` | `false` | Routes chat through LiteLLM multi-provider orchestrator |
| `ORCHESTRATOR_MAX_FAILOVERS` | `3` | Max cross-provider failover attempts before mock fallback |

---

## Security

### Authentication Model

- **Single-user by default**: no account setup required. The backend creates a default local identity on first boot.
- **Optional bearer token**: set `MIORI_API_TOKEN` in `services/core-api/.env` to enforce `Authorization: Bearer <token>` on all REST endpoints. When unset, the API is open and returns a DEV user.
- **Device pairing**: future WAN remote control uses hash-based pairing secrets (Mark-XLVI patterns). Current pairing is mocked in `services/core-api/app/models/device.py`.

### Trust Levels

Computer-use capability is unrestricted once enabled. Trust levels control **approval speed**, not capability:

| Level | Auto-approves | Prompts user for |
| --- | --- | --- |
| `manual` | nothing | every tool call |
| `auto-shell` | shell, fs_write, fs_read, fs_list, screenshot, type, keypress | install, browser, process_kill, service, delete |
| `trusted` | everything except `cmd /c` or `powershell` on Windows | rare high-risk escalations |
| `god` | everything, no prompts | nothing |

Default: `manual`. Configurable per device.

### Computer-Use Safety

- `COMPUTER_USE_ENABLED` defaults to `false`. It must be explicitly turned on.
- **Arm/disarm endpoints**: `POST /api/settings/computer-use/arm` and `/disarm` require explicit user action.
- **Audit log**: every arm, disarm, and tool invocation is append-only logged at `data/computer_use_audit.log` and readable via `GET /api/settings/computer-use/audit`.
- **Undo log**: `fs_delete` records deleted content in an in-memory ring buffer (last 100 deletions) for recovery.
- **Approval gate**: tools with `requires_approval=True` pause execution and broadcast a `tool_approval` (chat) or `step_approval_needed` (plans) event over `/ws/status`. The frontend must `POST /api/tools/approve` or `POST /api/plans/{id}/steps/{step_id}/approve` before execution proceeds.

### Sandbox Notes

No sandbox is enforced. Computer-use and shell tools run with the same privileges as the logged-in user. The security model is **observe everything, enable instant abort, reversible where possible**. WAN exposure without proper network controls is **not recommended**.

---

## Testing

```bash
# Backend — pytest
cd services/core-api
source .venv/bin/activate
pytest

# Backend — plan tests only
cd services/core-api
MIORI_SKIP_DEV=1 python -m pytest tests/test_plans.py -q

# Frontend lint
pnpm lint

# Frontend typecheck
pnpm typecheck

# Frontend build (Vite)
pnpm build
```

Pre-commit hooks and CI workflows are scaffolded in `scripts/` and the repo root.

---

## Deployment

### Docker

A production Docker setup is planned. The current scaffold targets local-first deployment with SQLite.

### Static Hosting (Remote Dashboard)

The remote dashboard is a static SPA. After `pnpm --filter @miori/remote-dashboard build`, the `dist/` output can be served from any static host (Nginx, Cloudflare Pages, Vercel, etc.) pointed at the backend API.

### Compose Notes

When Docker support lands, the expected compose topology is:

- `core-api` — FastAPI + Uvicorn, SQLite volume
- `desktop` — Tauri build artifact (per-OS installer)
- `remote-dashboard` — Nginx + built SPA

---

## Contributing

Miori Core is open to contributions. Before you start:

1. Read [`MISSION.md`](./MISSION.md) — the product north star and hard constraints.
2. Review [`docs/feature-matrix.md`](./docs/feature-matrix.md) and [`TASKS.md`](./TASKS.md) — the capability map and roadmap.
3. Follow the **module ownership boundaries** in [`docs/architecture/system-overview.md`](./docs/architecture/system-overview.md#7-module-ownership-boundaries).
4. No blind code imports. Harvest ideas from donor repos; re-implement cleanly inside the destination module.
5. Keep lite mode the default. Heavy features must lazy-load and degrade gracefully.

Bug reports, design feedback, and pull requests are welcome.

---

## License

MIT © 2026 Cobalt — see [`LICENSE`](./LICENSE).

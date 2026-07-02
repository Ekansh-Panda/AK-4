<div align="center">

# Miori Core

**A cross-platform personal AI friend, workstation, and remote desktop companion.**

_Warm. Sharp. Present. A friend, not a servant._

</div>

---

Miori Core is the foundation of Miori — a personal AI you actually live alongside:
a desktop companion you talk to, a workspace you think in, and a remote presence
you can reach from your phone. This repository is a clean, modular monorepo with a
buildable, wired-up spine. The deeper intelligence (semantic memory, computer-use,
voice, multi-agent) is scaffolded behind clean interfaces and lands in later phases
— see [`TASKS.md`](./TASKS.md).

> **Status:** v1. The desktop app and remote dashboard are wired to the backend
> over REST + WebSocket, with **real model providers** (OpenAI / OpenAI-compatible
> / Gemini), SQLite **persistence**, and **file text ingestion**. It still boots
> fully offline with a **mock provider** (zero API keys) and runs in **lite mode**
> by default so it stays usable on low-end machines.

## What's in the box

```
miori-core/
├─ apps/
│  ├─ desktop/            # Tauri v2 + React + TS + Tailwind — the companion UI
│  └─ remote-dashboard/   # Mobile-first React web app — reach Miori from your phone
├─ services/
│  └─ core-api/           # FastAPI backend — chat, memory, providers, persona, remote…
├─ packages/
│  ├─ ui/                 # Shared design tokens
│  ├─ types/              # Shared TypeScript contracts (mirror of the API schemas)
│  ├─ prompts/            # Persona prompt packs (friend / operator / researcher / coder)
│  └─ config/            # Shared tsconfig + Tailwind preset (the Miori design tokens)
├─ integrations/          # Donor repos cloned here for analysis & selective harvesting
├─ docs/                  # Architecture, repo analyses, feature matrix, UI spec
├─ scripts/               # install, bootstrap, run-dev, env-validate, db-init (.sh/.ps1)
├─ MISSION.md             # The product north star
└─ TASKS.md               # Roadmap: v0.1 → v0.2 → v0.3
```

## Tech stack

| Layer | Choice |
| --- | --- |
| Desktop shell | Tauri v2 · React · TypeScript · Vite · TailwindCSS · Framer Motion |
| Remote dashboard | React · TypeScript · Vite · Tailwind (mobile-first) |
| Backend | Python 3.11+ · FastAPI · Uvicorn · Pydantic v2 |
| Data | SQLAlchemy 2.x · SQLite (default) |
| Realtime | WebSocket streaming (`/ws/chat`, `/ws/status`, `/ws/remote`) |
| Design | Minimal, dark, glassy, one warm accent — a presence, not a cockpit |

Built to stay usable on **low-end machines**: SQLite by default, a "lite mode"
that keeps heavy/optional dependencies (vector DB, embeddings) lazy and off.

## Quick start

Prerequisites: **Python 3.11+**, **Node 18+**, **pnpm**, and (for the native
desktop build) the [Tauri prerequisites](https://tauri.app/start/prerequisites/).
You can run the web UIs without the Tauri toolchain.

```bash
# 0) One-command install (creates .env, venv, deps, database)
bash scripts/install.sh              # Windows: scripts\install.ps1

# (optional) sanity-check your toolchain + provider keys
bash scripts/env-validate.sh         # Windows: scripts\env-validate.ps1

# 1) Run a piece (or all of them)
bash scripts/run-dev.sh api          # FastAPI on http://127.0.0.1:8000 (docs at /docs)
bash scripts/run-dev.sh desktop      # Desktop (Vite) on http://localhost:1420
bash scripts/run-dev.sh remote       # Remote dashboard on http://localhost:5174
bash scripts/run-dev.sh all          # everything together
```

Then open the desktop UI at <http://localhost:1420>. The backend is optional for
the shell — the frontends fall back to mock data when it isn't running — but it's
needed for real chat, persistence, and providers.

**Full setup guide:** [`docs/setup/INSTALLATION.md`](./docs/setup/INSTALLATION.md)
(prerequisites per OS, Tauri toolchain, `.env`, DB init, native builds,
troubleshooting).

Per-component instructions:
- Backend — [`services/core-api/README.md`](./services/core-api/README.md)
- Desktop — [`apps/desktop/README.md`](./apps/desktop/README.md)
- Remote — [`apps/remote-dashboard/README.md`](./apps/remote-dashboard/README.md)

### Providers

Mock works offline with no keys. For real replies set keys in
`services/core-api/.env` (`OPENAI_API_KEY`, or `OPENAI_BASE_URL` for OpenRouter /
local servers, or `GEMINI_API_KEY`) and pick the active provider in the desktop
**Settings** page. See
[Provider API key setup](./docs/setup/INSTALLATION.md#11-provider-api-key-setup).

### Where data lives

Local state is created on first backend boot, relative to `services/core-api/`:
the SQLite DB at `miori.db` (`DATABASE_URL`) and uploads in `data/uploads/`
(`UPLOAD_DIR`). Initialize the DB without starting the server via
`scripts/db-init.sh` (Windows: `scripts\db-init.ps1`).

## Architecture at a glance

The desktop app and remote dashboard talk to `core-api` over REST (`/api/*`) and
WebSocket (`/ws/*`). The backend is organised around swappable service
abstractions so the spine stays stable while implementations grow:

`MemoryService` · `ProviderRegistry` · `ToolRegistry` · `PersonaService` ·
`RemoteSessionService` · `TaskService` · `FileIngestionService`

Full details: [`docs/architecture/system-overview.md`](./docs/architecture/system-overview.md).

## Documentation

| Doc | What it covers |
| --- | --- |
| [`docs/setup/INSTALLATION.md`](./docs/setup/INSTALLATION.md) | Full install/setup + troubleshooting (per OS) |
| [`MISSION.md`](./MISSION.md) | Product north star and constraints |
| [`docs/architecture/`](./docs/architecture/) | System overview, data model, API surface |
| [`docs/feature-matrix.md`](./docs/feature-matrix.md) | Capability → donor repo → destination module → priority |
| [`docs/repo-analysis/`](./docs/repo-analysis/) | Engineering analyses of donor repos |
| [`docs/ui-spec/`](./docs/ui-spec/) · [`apps/desktop/UI_SPEC.md`](./apps/desktop/UI_SPEC.md) | Visual language & design system |
| [`TASKS.md`](./TASKS.md) | Roadmap and backlog |

## Design principles

- **Friend, not servant.** Miori has warmth, taste, and a point of view.
- **Calm, not a cockpit.** Minimal, dark, glassy; subtle motion; generous space.
- **Low-end first.** Lazy-load heavy features; SQLite + lite mode by default.
- **Interfaces over fake complexity.** Where something isn't built yet, there's a
  clean interface and a `TODO`, not pretend logic.

## License

MIT © 2026 Cobalt — see [`LICENSE`](./LICENSE).

# Miori Core — Overnight Build Plan (v0.1)

> Record of the **v0.1 overnight foundation build**: the assembly-line job plan, folder ownership,
> what ships as scaffold vs mock vs deferred, and the pre-sleep checklist.
>
> Goal (from [MISSION.md](../../MISSION.md)): **a working v0.1 foundation, not a finished AI.**
> Everything compiles or is cleanly scaffolded; unimplemented features ship as clean interfaces + TODOs + docs.
>
> Related: [System Overview](../architecture/system-overview.md) · [Feature Matrix](../feature-matrix.md) · [API Surface](../architecture/api-surface.md) · [TASKS.md](../../TASKS.md)

---

## 1. The 6-job assembly line

Six parallel jobs, each owning a disjoint set of folders to avoid collisions.

| # | Job | Owns | Delivers |
|---|---|---|---|
| **1** | **Monorepo + desktop shell** | `apps/desktop/` (incl. `src-tauri/`) | Tauri + React + TS + Tailwind shell, 8 feature pages, layout, presence orb stub, API client in `lib/`, state in `state/` |
| **2** | **Remote dashboard** | `apps/remote-dashboard/` | React/TS web shell sharing the same API contract; device list + presence (mock) |
| **3** | **Core API backend** | `services/core-api/` (`routers/`, `ws/`, `services/`, `schemas/`) | FastAPI app, REST `/api/*`, WS `/ws/*`, service-layer abstractions (memory/providers/tools/persona/remote/tasks/files), models already present in `models/` |
| **4** | **Shared design system + prompts** | `packages/{ui,types,prompts}` | Tailwind tokens, shadcn-based primitives, shared TS types, persona prompt profiles |
| **5** | **Repo analysis docs** | `docs/repo-analysis/` | Donor-repo (Mark-XLVI, Odysseus, Khoj, computer-use) analysis — *owned by another job, not this one* |
| **6** | **Architecture + integration docs** *(this job)* | `docs/architecture/`, `docs/ui-spec/`, `docs/overnight-plan/`, `docs/feature-matrix.md`, root `TASKS.md` | Feature matrix, system overview, data model, API surface, visual direction, this plan, roadmap |

> Jobs 1–4 produce code/scaffold; jobs 5–6 produce docs. The DB models in
> `services/core-api/app/models/*` already exist and are the shared contract all jobs reference.

---

## 2. Folder ownership map

Strict, non-overlapping ownership keeps the assembly line conflict-free
(mirrors [system-overview §7](../architecture/system-overview.md#7-module-ownership-boundaries)):

```
apps/desktop/            → Job 1   (native shell + UI pages)
apps/remote-dashboard/   → Job 2   (web dashboard)
services/core-api/       → Job 3   (FastAPI: routers, ws, services, schemas)
  └ app/models/          → shared contract (pre-built)
packages/ui|types|prompts→ Job 4   (design system, shared types, persona prompts)
docs/repo-analysis/      → Job 5   (donor analysis) — DO NOT TOUCH from job 6
docs/architecture/       → Job 6 (this job)
docs/ui-spec/            → Job 6 (this job)
docs/overnight-plan/     → Job 6 (this job)
docs/feature-matrix.md   → Job 6 (this job)
TASKS.md (root)          → Job 6 (this job)
README.md (root)         → Job 1 / monorepo owner
```

This job (6) wrote **only** the docs paths above and touched **no code** and **not** `docs/repo-analysis/`.

---

## 3. Scaffold vs mocked vs deferred

### Delivered as scaffold (compiles / boots, structurally real)
- Monorepo layout (`apps/`, `services/`, `packages/`).
- Desktop Tauri shell + 8 feature pages + layout + state.
- Remote dashboard shell.
- FastAPI app with `/api/*` routers and `/ws/*` handlers registered.
- SQLAlchemy models for all 8 tables + SQLite session/engine (`db/`).
- Service-layer package skeletons (memory/providers/tools/persona/remote/tasks/files).
- Shared design tokens + persona prompt profiles in `packages/`.
- Config with `LITE_MODE` + `REMOTE_ENABLED` flags (`core/config.py`).

### Delivered as mocked (wired, canned/echo behavior)
- Chat streaming over `/ws/chat` (echo provider).
- Status heartbeat over `/ws/status`.
- Memory store + keyword search (no embeddings).
- Provider listing (`echo` only), persona modes, remote device presence.
- CRUD persistence to SQLite is **real** even where intelligence is mocked.

### Deferred (interface + TODO + docs only)
- Real model providers (OpenAI/Anthropic/Ollama/local) with lazy imports.
- Semantic/vector memory retrieval.
- File ingestion/index pipeline.
- Real remote transport + device pairing secrets.
- Computer-use action execution + frames.
- Task scheduler (APScheduler) + recurring jobs.
- Voice pipeline (STT/TTS) + reactive orb audio.
- Multi-agent orchestration.

Full schedule for flipping these: [TASKS.md](../../TASKS.md).

---

## 4. Pre-sleep checklist

Before walking away from the v0.1 build, confirm:

- [ ] Monorepo structure exists (`apps/`, `services/`, `packages/`).
- [ ] `services/core-api` boots with **no optional/heavy deps** (FastAPI + SQLAlchemy + SQLite only).
- [ ] `GET /api/health` returns version + `lite_mode`/`remote_enabled` flags.
- [ ] SQLite DB initializes and all 8 tables are created on first run.
- [ ] `/ws/chat` echoes a streamed reply; messages persist to `messages`.
- [ ] Desktop shell builds and renders all 8 pages without runtime errors.
- [ ] Remote dashboard builds and shows the (mock) device list.
- [ ] `packages/ui` tokens + persona prompts are importable by both apps / the API.
- [ ] `LITE_MODE=True` is the default; app is fully clickable with **zero API keys**.
- [ ] README has run instructions for backend + both frontends (owned by Job 1).
- [ ] Docs cross-link and are committed: feature matrix, system overview, data model, API surface, visual direction, this plan, TASKS.md.
- [ ] No file outside each job's owned folders was modified.

If every box is checked, v0.1 is a clean, honest foundation: it runs, it's modular, and the gaps are documented — not hidden.

# Miori Core — Integration Feature Matrix

> Master mapping of **Miori Core capabilities → donor repositories → concrete destination modules**.
>
> Donor repos are used for **ideas, architecture analysis, and selective feature harvesting only**.
> We do **not** dump donor code into this repo (see [MISSION.md](../MISSION.md) hard constraints).
>
> Related docs:
> [System Overview](architecture/system-overview.md) ·
> [Data Model](architecture/data-model.md) ·
> [API Surface](architecture/api-surface.md) ·
> [Visual Inspirations](ui-spec/visual-inspirations.md) ·
> [Overnight Build Plan](overnight-plan/build-plan.md) ·
> [Roadmap / TASKS.md](../TASKS.md)

---

## Legend

**Priority**

| Tag | Meaning |
|-----|---------|
| **P0** | Foundation for v0.1 — must exist as scaffold/interface tonight |
| **P1** | Integration phase (v0.2) — wired with real backends |
| **P2** | Advanced (v0.3) — automation, voice, multi-agent, packaging |

**Status**

| Tag | Meaning |
|-----|---------|
| **mocked** | Interface + stub/fake implementation present; returns canned/echo data |
| **implemented** | Real working behavior end-to-end |
| **planned** | Documented interface/TODO only; no runtime behavior yet |

**Donor repos**

| Repo | Used for |
|------|----------|
| **Mark-XLVI / MARK-XL** | Remote control + device pairing patterns, operator persona feel, desktop companion UX |
| **Odysseus** | Semantic memory store, retrieval/ranking ideas, agent loop structure |
| **Khoj** | File ingestion + indexing pipeline, search-over-documents, scheduled tasks/automation |
| **computer-use repos** (e.g. Anthropic computer-use, OpenInterpreter-style) | Tool registry shape, sandboxed action execution, screen/keyboard/mouse control contracts |

---

## Capability → Donor → Destination

| Capability | Source Repo(s) | What To Take | Destination Module (concrete path) | Priority | Status |
|---|---|---|---|---|---|
| **Remote dashboard** | Mark-XLVI / MARK-XL | Device list + presence UI, pairing/handshake flow, lightweight control surface (not a cockpit) | `apps/remote-dashboard/` · `services/core-api/app/routers/remote.py` · `services/core-api/app/ws/remote.py` | P0 | mocked |
| **Workspace tabs (pages)** | Mark-XLVI (layout ideas only) | Tabbed workspace shell: Chat, Files, Memory, Projects, Research, Tasks, Remote, Settings | `apps/desktop/src/features/{chat,files,memory,projects,research,tasks,remote,settings}/` · `apps/desktop/src/components/layout/` | P0 | mocked |
| **Semantic memory** | Odysseus, Khoj | Namespaced memory store, write/search/recall API, ranking ideas. Embeddings stay optional | `services/core-api/app/services/memory/` · `services/core-api/app/models/memory.py` · `services/core-api/app/routers/memory.py` | P0→P1 | implemented |
| **Persona system** | Mark-XLVI (operator tone), Odysseus (agent voice) | Persona modes (friend/operator/researcher/coder), warm friend-first system prompts, prompt profiles | `services/core-api/app/services/persona/` · `packages/prompts/` · `services/core-api/app/routers/persona.py` | P0 | implemented |
| **Model/provider abstraction** | Odysseus, computer-use repos | Provider interface (chat/stream/embed), pluggable OpenAI/Anthropic/Ollama/local, lite default | `services/core-api/app/services/providers/` · `services/core-api/app/routers/providers.py` | P0→P1 | implemented |
| **Tool registry** | computer-use repos, Odysseus | Tool descriptor schema, register/list/invoke contract, capability gating | `services/core-api/app/services/tools/` | P0 | implemented |
| **Computer-use** | computer-use repos, Mark-XLVI | Sandboxed action contracts (screenshot, click, type, shell), safety gating, opt-in only | `services/core-api/app/services/tools/` (computer-use tools) · `services/core-api/app/routers/remote.py` | P2 | planned |
| **File ingestion** | Khoj | Upload → store metadata → ingest/index pipeline, doc parsing, search-over-files | `services/core-api/app/services/files/` · `services/core-api/app/models/file.py` · `services/core-api/app/routers/files.py` | P1 | implemented |
| **Tasks / automation** | Khoj (scheduler), Mark-XLVI | Task CRUD, status lifecycle, scheduled/recurring jobs (APScheduler later) | `services/core-api/app/services/tasks/` · `services/core-api/app/models/task.py` · `services/core-api/app/routers/tasks.py` | P0→P2 | implemented |
| **Projects** | Khoj (workspace ideas) | Project workspace linking sessions/tasks/files; CRUD + brief | `services/core-api/app/models/project.py` · `services/core-api/app/routers/projects.py` · `apps/desktop/src/features/projects/` | P1→P2 | implemented |
| **Research** | Odysseus (research agent) | Background research agent, persisted findings, memory row (`kind="research"`) | `services/core-api/app/models/research.py` · `services/core-api/app/routers/research.py` · `services/core-api/app/services/memory/` | P1→P2 | implemented |
| **Auth (single-user)** | — | Real local identity (`miori-local` user on first boot), `default_user_id` in settings, `MIORI_API_TOKEN` still enforced when set | `services/core-api/app/core/auth.py` · `services/core-api/app/models/user.py` | P1 | implemented |
| **Voice** | computer-use repos (I/O patterns) | STT/TTS pipeline contract, push-to-talk + presence-orb reactive audio | `services/core-api/app/services/providers/` (voice provider, OpenAI Whisper/TTS) · `apps/desktop/src/features/chat/` (push-to-talk) | P2 | implemented |
| **Chat streaming** | Odysseus, Mark-XLVI | Token streaming over WebSocket, partial-message UX, cancel/regenerate | `services/core-api/app/ws/chat.py` · `services/core-api/app/services/providers/` · `apps/desktop/src/features/chat/` | P0 | implemented |

---

## Cross-cutting capabilities

| Capability | Source Repo(s) | What To Take | Destination Module (concrete path) | Priority | Status |
|---|---|---|---|---|---|
| **Presence orb / identity** | Inspiration only (Jarvis/HoloJarvis — visual cue, **not** architecture) | A single living "presence" element that breathes/reacts; friend-not-cockpit feel | `apps/desktop/src/components/` (PresenceOrb) · see [visual-inspirations](ui-spec/visual-inspirations.md) | P1 | planned |
| **Shared design system** | shadcn/ui + Tailwind | Tokens, glassy dark theme, shared UI primitives across desktop + dashboard | `packages/ui/` · `apps/desktop/src/components/ui/` · `apps/*/tailwind.config.ts` | P0 | mocked |
| **WebSocket status bus** | Mark-XLVI | Live status/heartbeat channel (device + task + provider health + research + tool_approval + presence-orb) | `services/core-api/app/ws/status.py` · `apps/desktop/src/state/` | P0 | implemented |
| **Settings / config** | — | Key/value settings, lite-mode + feature flags surfaced to UI | `services/core-api/app/models/setting.py` · `services/core-api/app/routers/settings.py` · `services/core-api/app/core/config.py` | P0 | implemented |
| **Multi-agent orchestration** | Odysseus | Agent loop + sub-agent delegation over the tool registry | `services/core-api/app/services/` (orchestrator, future) | P2 | planned |

---

## Notes

- **No blind code import.** Every row above means *harvest the idea/contract*, then re-implement cleanly inside the destination module. Donor licensing and architecture mismatch make a direct merge a non-goal (MISSION.md: "New architecture, not direct repo-merging").
- **Lite by default.** `LITE_MODE=True` and `DATABASE_URL=sqlite:///./miori.db` are the defaults (`services/core-api/app/core/config.py`). Any "heavy" row (real providers, vector memory, computer-use, voice) must lazy-load its dependencies and degrade gracefully when disabled. See low-end rules in [system-overview](architecture/system-overview.md#low-end-machine-optimization-rules).
- **Mocked-tonight rows become P1/P2 work.** The single source of truth for what flips from `mocked` → `implemented` is [`TASKS.md`](../TASKS.md). This matrix is the *map*; TASKS.md is the *schedule*.
- **Computer-use and voice are opt-in P2.** Voice (STT/TTS) is implemented via OpenAI Whisper/TTS with mock fallback. Host-action computer-use tools are implemented but the `/ws/remote` frame streaming is still P2 (not fully wired).
- **Persona is the product.** "Friend, not servant." Persona mode defaults to `friend` (`services/core-api/app/models/session.py`), prompt profiles live in `packages/prompts/`.
- The `packages/` directory (shared `ui`, `prompts`, `types`) is referenced throughout and is owned by the scaffold/shared-design jobs (see [overnight build plan](overnight-plan/build-plan.md)).

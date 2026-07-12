# Miori Core — API Surface

> The contract between the frontends (`apps/desktop`, `apps/remote-dashboard`) and the brain
> (`services/core-api`). Two transports: **REST `/api/*`** and **WebSocket `/ws/*`**.
>
> Status tags reflect the current v1.2.0 reality: core intelligence, providers, file
> ingestion, memory, tasks, execution plans, agentic tools, continuous vision, audio
> context, self-evolving persona, voice, projects, research, a real `/ws/status`
> fan-out bus, tools/plan approval, single-user auth, and a real remote pairing →
> bearer-token flow are **implemented**. Remote WAN transport and high-latency frame
> streaming remain **mocked/planned** (intentionally, per constraints).
>
> Related: [System Overview](system-overview.md) · [Data Model](data-model.md) · [Feature Matrix](../feature-matrix.md)

Conventions:
- Base URL defaults to `http://127.0.0.1:8000` (`core/config.py`).
- All bodies are JSON. IDs are string UUIDs.
- Routers live in `services/core-api/app/routers/`; WS handlers in `services/core-api/app/ws/`.
- **Status**: `mock` = wired, returns stub/echo data · `planned` = documented only.

---

## REST `/api`

### Health — `/api/health` · `routers/health.py`
| Method | Path | Notes | Status |
|---|---|---|---|
| GET | `/api/health` | Liveness + version + flags (`lite_mode`, `remote_enabled`). Used by status bar / dashboard handshake. | **mock → implemented** (real, trivial) |

### Chat — `/api/chat` · `routers/chat.py`
REST handles session CRUD + history; live streaming is on `/ws/chat`.
| Method | Path | Request | Response | Status |
|---|---|---|---|---|
| GET | `/api/chat/sessions` | — | list of `ChatSession` | implemented |
| POST | `/api/chat/sessions` | `{title?, persona_mode?}` | created `ChatSession` | implemented |
| GET | `/api/chat/sessions/{id}/messages` | — | list of `Message` | implemented |
| POST | `/api/chat/sessions/{id}/messages` | `{role, content}` | persisted `Message` (non-streaming fallback) | implemented |
| DELETE | `/api/chat/sessions/{id}` | — | `{ok}` | implemented |

### Memory — `/api/memory` · `routers/memory.py`
| Method | Path | Request | Response | Status |
|---|---|---|---|---|
| GET | `/api/memory` | `?namespace=` | list of `Memory` | implemented |
| POST | `/api/memory` | `{namespace?, content, meta?}` | created `Memory` | implemented |
| POST | `/api/memory/search` | `{query, k?}` | ranked memories (lite: text match) | implemented |
| DELETE | `/api/memory/{id}` | — | `{ok}` | implemented |

> Vector/semantic search is **implemented** via ChromaDB; lite search is substring/keyword only.

### Files — `/api/files` · `routers/files.py`
| Method | Path | Request | Response | Status |
|---|---|---|---|---|
| GET | `/api/files` | — | list of `FileRecord` | implemented |
| POST | `/api/files` | multipart upload | `FileRecord` (`status=uploaded`) | implemented |
| POST | `/api/files/{id}/ingest` | — | `FileRecord` (`status=ingesting`→`ingested`) — **triggers async pipeline** | implemented |
| GET | `/api/files/{id}` | — | `FileRecord` | implemented |
| DELETE | `/api/files/{id}` | — | `{ok}` | implemented |
| GET | `/api/files/search` | `?q=&k=` | ranked `FileChunk` results (semantic when `SEMANTIC_MEMORY_ENABLED`, else substring) | implemented |

### Providers — `/api/providers` · `routers/providers.py`
| Method | Path | Request | Response | Status |
|---|---|---|---|---|
| GET | `/api/providers` | — | available providers + configured state (lite: `echo`) | implemented |
| GET | `/api/providers/models` | `?provider=` | model list | implemented |
| GET | `/api/providers/status` | — | list of `{name, configured, available, active, reachable}` per provider | implemented |
| GET | `/api/providers/ping` | `?refresh=` | cached reachability map (≈60s TTL) | implemented |
| POST | `/api/providers/select` | `{provider, model}` | persisted to `settings` | implemented |

> Real OpenAI/Anthropic/Gemini/Groq/Mistral/SambaNova/Cohere/HuggingFace/Cloudflare providers are **implemented**, lazy-imported per provider.

### Persona — `/api/persona` · `routers/persona.py`
| Method | Path | Request | Response | Status |
|---|---|---|---|---|
| GET | `/api/persona/modes` | — | `[friend, operator, researcher, coder]` + descriptions | implemented |
| GET | `/api/persona` | — | active persona config | implemented |
| POST | `/api/persona` | `{mode}` | updated persona | implemented |

> Prompt profiles sourced from `packages/prompts/`; service degrades gracefully if the dir is missing.

### Remote — `/api/remote` · `routers/remote.py`
Gated by `REMOTE_ENABLED`. Pairing flow: desktop generates a 6-char code → remote
dashboard submits it → backend returns a bearer token → token is used for
REST + `/ws/remote` WebSocket auth.

| Method | Path | Request | Response | Status |
|---|---|---|---|---|
| POST | `/api/remote/devices` | `{name, platform?, user_id?}` | created `Device` | implemented |
| GET | `/api/remote/devices` | — | list of `Device` (persisted) | implemented |
| POST | `/api/remote/devices/{id}/pairing-code` | — | `PairingCodeOut` (single-use 6-char code) | implemented |
| POST | `/api/remote/pair` | `{device_id, code}` | `PairResponse` with bearer `token` | implemented |
| POST | `/api/remote/devices/{id}/unpair` | — | updated `Device` | implemented |
| POST | `/api/remote/devices/{id}/wake` | — | updated `Device` + WS broadcast | implemented |
| POST | `/api/remote/devices/{id}/sleep` | — | updated `Device` + WS broadcast | implemented |
| GET | `/api/remote/presence` | — | `PresenceOut` with connected count + devices | implemented |
| POST | `/api/remote/devices/{id}/sessions` | — | created `RemoteSession` | implemented |
| GET | `/api/remote/sessions` | — | list of `RemoteSession` | implemented |
| DELETE | `/api/remote/sessions/{id}` | — | `{ok}` | implemented |

### Tasks — `/api/tasks` · `routers/tasks.py`
| Method | Path | Request | Response | Status |
|---|---|---|---|---|
| GET | `/api/tasks` | `?status=` | list of `Task` | implemented |
| POST | `/api/tasks` | `{title, description?, due_at?}` | created `Task` | implemented |
| PATCH | `/api/tasks/{id}` | `{status?, title?, ...}` | updated `Task` | implemented |
| DELETE | `/api/tasks/{id}` | — | `{ok}` | implemented |

> Scheduling / recurring jobs (APScheduler) are **implemented**.

### Settings — `/api/settings` · `routers/settings.py`
| Method | Path | Request | Response | Status |
|---|---|---|---|---|
| GET | `/api/settings` | — | merged config flags + key/value `settings` | implemented |
| PUT | `/api/settings/{key}` | `{value}` | updated `Setting` | implemented |
| POST | `/api/settings/computer-use/arm` | — | `{detail: "armed"}` | implemented |
| POST | `/api/settings/computer-use/disarm` | — | `{detail: "disarmed"}` | implemented |
| GET | `/api/settings/computer-use` | — | `ComputerUseSettings` (trust_level, max_steps, timeout, vision/audio/double_verify/browser toggles) | implemented |
| PUT | `/api/settings/computer-use` | `ComputerUseSettings` | updated `ComputerUseSettings` | implemented |
| GET | `/api/settings/computer-use/audit` | — | list of audit logs | implemented |

### Plans — `/api/plans` · `routers/plans.py`
| Method | Path | Request | Response | Status |
|---|---|---|---|---|
| POST | `/api/plans` | `{goal, parallel?, trust_level?, steps?}` | created `TaskPlan` | implemented |
| GET | `/api/plans` | — | list of `TaskPlan` for current user | implemented |
| GET | `/api/plans/{id}` | — | `PlanDetail` (plan + steps) | implemented |
| POST | `/api/plans/{id}/cancel` | — | updated `TaskPlan` (`cancelled`) | implemented |
| POST | `/api/plans/{id}/steps/{step_id}/approve` | — | `{detail: "approved"}` | implemented |
| POST | `/api/plans/{id}/steps/{step_id}/retry` | — | updated `PlanStep` (retried) | implemented |
| POST | `/api/plans/{id}/subplans` | `{parent_step_id, goal, trust_level?}` | created child `TaskPlan` | implemented |

> Plans are decomposed by `PlannerService` into atomic steps, executed by `ExecutorService` with approval, replan, and parallel-batch support. WS events (`plan_created`, `plan_started`, `step_started`, `step_completed`, `step_failed`, `step_approval_needed`, `plan_completed`, `plan_failed`, `plan_cancelled`, `subplan_created`, `verification_attached`) fan out over `/ws/status`.

### Tools — `/api/tools` · `routers/tools.py`
| Method | Path | Request | Response | Status |
|---|---|---|---|---|
| GET | `/api/tools/pending` | — | list of pending `tool_call_id` strings | implemented |
| POST | `/api/tools/approve` | `{tool_call_id}` | `{detail: "approved"}` | implemented |
| POST | `/api/tools/reject` | `{tool_call_id}` | `{detail: "rejected"}` | implemented |

> The tool registry includes unrestricted agentic tools: `shell` (list-of-args, no shell=True), `fs_write`/`fs_read`/`fs_list`/`fs_delete` (with undo log), `browser` (Playwright, gated by `COMPUTER_USE_BROWSER_ENABLED`), `install`, `process`, `service`, `clipboard`, `notify`, `git`, `docker`. Tools with `requires_approval=True` pause the ReAct loop (chat) or executor (plans) and broadcast a `tool_approval` or `step_approval_needed` event over `/ws/status`.

### Audio — `/api/audio` · `routers/audio.py`
| Method | Path | Request | Response | Status |
|---|---|---|---|---|
| POST | `/api/audio/transcribe` | multipart `file` | `{text}` (Whisper when `OPENAI_API_KEY` present, mock fallback) | implemented |
| POST | `/api/audio/synthesize` | `{text, voice?}` | `audio/mpeg` bytes (OpenAI TTS when key present, mock fallback) | implemented |

> Desktop Composer has push-to-talk: `MediaRecorder` captures audio → `POST /api/audio/transcribe`. The voice provider is lazy-loaded and degrades to a mock when no key is configured.

### Projects — `/api/projects` · `routers/projects.py`
| Method | Path | Request | Response | Status |
|---|---|---|---|---|
| GET | `/api/projects` | `?status=` | list of `Project` (with linked sessions/tasks/files) | implemented |
| POST | `/api/projects` | `{name, description?, brief?, session_ids?, task_ids?, file_ids?}` | created `Project` | implemented |
| GET | `/api/projects/{id}` | — | `Project` (with linked sessions/tasks/files) | implemented |
| PATCH | `/api/projects/{id}` | `{name?, description?, status?, brief?, session_ids?, task_ids?, file_ids?}` | updated `Project` | implemented |
| DELETE | `/api/projects/{id}` | — | `{ok}` | implemented |

> `project_id` (string FK → `projects.id`, nullable, additive) is added to `chat_sessions`, `tasks`, and `files`; the `GET/PATCH/DELETE` responses include linked sessions/tasks/files.

### Research — `/api/research` · `routers/research.py`
| Method | Path | Request | Response | Status |
|---|---|---|---|---|
| POST | `/api/research` | `{query}` | `Research` (pending); runs a background research agent | implemented |
| GET | `/api/research` | — | list of `Research` | implemented |
| GET | `/api/research/{id}` | — | `Research` | implemented |
| DELETE | `/api/research/{id}` | — | `{ok}` | implemented |

> The background agent uses the active LLM provider, broadcasts `{type:"research",...}` over `/ws/status`, and ALSO persists a `memories` row with `kind="research"` (listable via `GET /api/memory?kind=research`).

---

## WebSocket `/ws`

All WS messages are JSON envelopes: `{ "type": "...", ... }`.

### `/ws/chat` · `ws/chat.py` — token streaming
- **Client → server:** `{type:"message", session_id, content}` · `{type:"cancel"}`
- **Server → client:** `{type:"token", delta}` (repeated) · `{type:"done", message_id}` · `{type:"error", detail}`
- Orchestrates persona → memory recall → provider stream → persist (see [chat data flow](system-overview.md#3-data-flow-for-a-chat-message)).
- **Status:** implemented (full agent tool-calling loop).

### `/ws/status` · `ws/status.py` — live status bus
- **Server → client:** `{type:"heartbeat", ts}` · `{type:"provider", state}` · `{type:"task", id, status}` · `{type:"device", id, state}` · `{type:"research", id, status}` · `{type:"tool_approval", ...}` · `{type:"plan_created", plan_id, goal, parallel, trust_level}` · `{type:"plan_started", plan_id}` · `{type:"plan_completed", plan_id, step_count}` · `{type:"plan_failed", plan_id, error}` · `{type:"plan_cancelled", plan_id, reason?}` · `{type:"step_started", plan_id, step_id, action?, replan?}` · `{type:"step_completed", plan_id, step_id}` · `{type:"step_failed", plan_id, step_id, error}` · `{type:"step_approval_needed", plan_id, step_id, action}` · `{type:"subplan_created", plan_id, sub_plan_id, parent_step_id}` · `{type:"verification_attached", plan_id, after_action, description}` · `{type:"presence", state}` (idle/listening/thinking/speaking/error)
- Feeds the desktop status bar / presence-orb state and the dashboard.
- **Status:** implemented (real event fan-out: task due, research, tool_approval, provider reachability, presence-orb state). Heartbeat is still emitted every 5s.

### `/ws/remote` · `ws/remote.py` — remote presence & control
- **Client → server:** `{type:"presence"}` · `{type:"command", action, device_id, ...}` · `{type:"frame", action, args}`
- **Server → client:** `{type:"presence", connected, devices}` · `{type:"command", ...}` · `{type:"frame_result", status, result}` · `{type:"error", detail}`
- Authentication: bearer `token` query param or `Authorization` header. Unauthenticated
  connections are observers (receive broadcasts but cannot send commands).
- Gated by `REMOTE_ENABLED`.
- **Status:** implemented (real pairing flow, bearer-token auth, presence broadcast,
  command relay, computer-use frame execution via `run_tool`).

---

## Implemented-as-mock vs planned (summary)

| Bucket | Endpoints |
|---|---|
| **Real** | `/api/health`, session/message/memory/task/file/setting **persistence**, `/ws/chat` streaming, `/api/providers` (+ `/status` + `/ping`), `/api/persona`, memory `search`, `/api/settings/computer-use/*`, `/api/plans` (CRUD + step approve/retry/subplans), `/api/tools` (approve/reject), `/api/files/search`, `/api/audio` (transcribe/synthesize), `/api/projects`, `/api/research`, real single-user `auth`, `/ws/status` event fan-out (plan/task/research/tool_approval/presence), `/api/remote` (/devices, /pair, /pairing-code, /wake, /sleep, /unpair, /presence, /sessions), `/ws/remote` command relay + frame execution |
| **Mock (wired, canned/echo)** | — |
| **Planned (interface/TODO only)** | real WAN remote transport, high-latency `/ws/remote` frame streaming |

The authoritative flip-list is [TASKS.md](../../TASKS.md); the capability→repo mapping is the [feature matrix](../feature-matrix.md).

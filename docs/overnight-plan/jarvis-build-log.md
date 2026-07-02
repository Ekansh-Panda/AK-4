# Jarvis Build Log

## Phase 0 — Audit
**What changed:** 
- Conducted full audit of `services/core-api/app/` code versus `api-surface.md`.
- Derived the true implementation status.

**Corrected API Surface Status Table:**

| Endpoint / Feature | Docs Status | Actual Code Status | Notes |
|---|---|---|---|
| `REST /api/chat/*` | mock | **REAL** | Full CRUD to SQLite via ChatService. |
| `REST /api/memory` | mock | **REAL** | Full CRUD implemented (SqliteMemoryProvider). |
| `REST /api/memory/search` | mock | **PARTIAL** | Substring search real; embeddings/vector search deferred. |
| `REST /api/files` | mock | **REAL** | Text/PDF extraction happens on upload and saves to DB. |
| `REST /api/files/{id}/ingest` | planned | **STUB** | Chunk/index pipeline deferred. |
| `REST /api/providers/*` | mock | **REAL** | Registry loads real SDKs (OpenAI, Gemini). Active selection persisted. |
| `REST /api/persona/*` | mock | **REAL** | Loads prompts from disk, fallback to built-ins. |
| `REST /api/remote/devices` | mock | **REAL** | CRUD implemented in RemoteSessionService. |
| `REST /api/remote/pair` | planned | **STUB** | Needs actual pairing secret logic. |
| `REST /api/remote/devices/{id}/wake` | planned | **STUB** | Needs WS relay. |
| `REST /api/tasks/*` | mock | **REAL** | Full CRUD to SQLite. |
| `REST /api/settings/*` | mock | **REAL** | SettingsService DB overrides active. |
| `WS /ws/chat` | mock | **REAL** | Fully streams tokens from active real provider. Memory recall hooks exist. |
| `WS /ws/status` | mock | **MOCK** | Heartbeat loop + canned events only. |
| `WS /ws/remote` | mock | **STUB** | In-memory session tracking, no real relay or computer-use yet. |

**What's flag-gated:** None
**What's still TODO:** Phases 1–10.

## Phase 1 — Memory: Semantic Recall
**What changed:** 
- `SEMANTIC_MEMORY_ENABLED` config flag added.
- `MemoryProvider` base class `add` and `search` are now `async`.
- `SqliteMemoryProvider` implements `async` hooks for base operations.
- `EmbeddingMemoryProvider` rewritten to use `registry.get().embed()` dynamically, with fallback to substring search.
- `MemoryService.add/search/summarize_session` made async.
- Memory routers updated to await memory functions.
- `ChatService` async functions `_recall_context` and `_store_facts` hooked correctly into `respond()` and `stream_response()`.

**What's flag-gated:** Vector embeddings require `SEMANTIC_MEMORY_ENABLED=True`.
**What's still TODO:** Phases 2–10.

## Phase 2 — Files: Ingestion & RAG
**What changed:**
- Added `POST /api/files/{id}/ingest` endpoint to `routers/files.py`.
- Implemented `FileIngestionService.ingest` to split text into chunks and store in semantic memory under `file:{id}` namespace.
- Updated `ChatService._recall_context` to search `file:%` namespace and inject file chunks into the LLM context.
- Graceful 400 error if `SEMANTIC_MEMORY_ENABLED` is false.

**What's flag-gated:** File ingestion requires `SEMANTIC_MEMORY_ENABLED=True`.
**What's still TODO:** Phases 3–10.

## Phase 3 — Remote: real transport and pairing
**What changed:**
- Added `pairing_secret_hash` and `bearer_token` to `Device` model.
- Created `POST /api/remote/devices/{id}/pairing-code` and `POST /api/remote/pair` endpoints.
- Rewrote `ws/remote.py` to require token authentication.
- Implemented real WS command relay for remote wake/sleep.
- Broadcast WS presence updates to the `/ws/status` channel.

**What's flag-gated:** Everything remote requires `REMOTE_ENABLED=True`.
**What's still TODO:** Phases 4–10.

## Phase 4 — Computer-Use Tool with Safety Sandbox
**What changed:**
- Added `COMPUTER_USE_ENABLED` and `COMPUTER_USE_SHELL_ENABLED` to config (default False).
- Added `/settings/computer-use/arm`, `disarm`, and `audit` endpoints.
- Implemented `ComputerUseTool` with screenshot, click, type, keypress, shell.
- Created robust safety audit log appended to `data/computer_use_audit.log`.
- Restricted shell execution to `data/computer_use_workspace/`.
- Exposed computer use in Settings tab in UI.
- Integrated `{type: "frame"}` remote WS relay to invoke computer use.

**What's flag-gated:** `COMPUTER_USE_ENABLED=True` required for arming.
**What's still TODO:** Phases 5–10.

## Phase 5 — Tasks & Background Scheduler
**What changed:**
- Installed APScheduler.
- Added `SCHEDULER_ENABLED` to config.
- Created `services/tasks/scheduler.py` with start/stop and job scheduling.
- Integrated scheduler into `main.py` lifespan and `TaskService` CRUD operations.

## Phase 6 — Audio (STT / TTS) [Optional/Deferred]
**What changed:**
- Created `routers/audio.py` with mocked `/transcribe` and `/synthesize` endpoints.
- Registered the router in `main.py`.

**What's still TODO:** Phases 7–10.
**Resume point:** Start Phase 7 (Agent Pipeline & Real Model wiring).

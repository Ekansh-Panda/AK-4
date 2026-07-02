# Odysseus — Repo Analysis

> Engineering due-diligence for Miori Core. Grounded in the public repo
> `github.com/pewdiepie-archdaemon/odysseus` (README + project page). Some
> implementation specifics come from secondary write-ups rather than the README
> itself and are labelled `[INFERRED]` / `[SECONDARY-SOURCE]`. Confirm against source
> before depending on them.

## 1. What the repo is
Odysseus is a self-hosted, local-first, privacy-first AI workspace that aims to give
a ChatGPT/Claude-class experience entirely on your own hardware with no telemetry. It
bundles chat + agents, deep research, model compare, a writing-first document editor,
email (IMAP/SMTP), notes/tasks/calendar, and a large "extras" surface (image editor,
themes, web search, presets, sessions, 2FA). It is model-agnostic across local and
cloud backends (vLLM, llama.cpp, Ollama, OpenRouter, OpenAI). For Miori Core it is the
**single most aligned donor** — almost a superset of the required pages and backend
modules — so it is the primary architectural template for the workspace half of the
product.

## 2. Tech stack
- **Backend:** Python, FastAPI entry point (`app.py`) with modules for auth, database, middleware, LLM core, agent loop, agent tools, chat, and search. `[SECONDARY-SOURCE]`
- **Frontend:** TypeScript + CSS/HTML (framework not named in README).
- **Database:** SQLite for sessions/messages (local `data/` dir). `[SECONDARY-SOURCE]`
- **Vector memory:** ChromaDB with fastembed (ONNX) embeddings for vector + keyword retrieval, with import/export. `[SECONDARY-SOURCE]`
- **Agent framework:** built on `opencode`; supports MCP, web, files, shell, skills, memory. `[SECONDARY-SOURCE]`
- **Web search:** SearXNG (bundled in compose). `[SECONDARY-SOURCE]`
- **Notifications:** ntfy + browser + email channels. `[SECONDARY-SOURCE]`
- **Models:** vLLM, llama.cpp, Ollama, OpenRouter, OpenAI.
- **Deployment:** Docker Compose (Odysseus + ChromaDB + SearXNG + ntfy, bound to 127.0.0.1); native installs on Linux/macOS (Apple Silicon Metal)/Windows.
- **License:** AGPL-3.0-or-later.

## 3. Standout features
- **Chat + Agents** with tools, MCP, files, shell, skills, and persistent memory.
- **Persistent memory + skills** — the agent evolves over time as it learns the user.
- **Deep Research** — multi-step web research with source reading and report generation.
- **Compare** — blind side-by-side model testing and synthesis.
- **Documents** — writing-first editor with AI edits/suggestions (Markdown/HTML/CSV).
- **Notes / Tasks / Calendar** — reminders, todos, cron-style scheduled agent tasks, CalDAV sync, ntfy/browser/email pings.
- **Cookbook** — hardware-aware model recommendation, download, and serving.
- **Local-first, no telemetry, 127.0.0.1 bind by default.**

## 4. Strengths
- **Module-for-module overlap with Miori's required pages** (Chat, Files, Memory, Research/Deep Research, Tasks) and backend modules — a near drop-in mental model.
- **FastAPI + SQLite + Chroma** matches Miori's mandated stack almost exactly (FastAPI, SQLAlchemy+SQLite default).
- **Model-agnostic provider layer** is a clean template for Miori's `providers` abstraction.
- **Memory architecture** (vector + keyword via Chroma/fastembed, import/export) is a concrete, proven design for Miori's `memory` module.
- **Local-first/privacy posture** matches Miori's self-hosted companion ethos.
- **Scheduled-agent-tasks + notification fan-out** is directly reusable for the Tasks page.

## 5. Limitations / weak points
- **AGPL-3.0** — strong copyleft. Copying code (vs. learning architecture) would impose AGPL on Miori. Mission already mandates "no direct repo-merging" — treat as **read-for-ideas only**.
- **Feature sprawl** — email, calendar, image editor, themes, 2FA, gallery far exceed v0.1 scope and pull against "minimal, low-end machine."
- **Heavy default footprint** — Chroma + SearXNG + ntfy + local model serving is a lot for low-end machines; conflicts with Miori's "heavy features optional/lazy-loaded."
- **Docker-Compose-centric** deployment differs from Miori's Tauri desktop + FastAPI shape.
- **UI is workspace/cockpit-style**, not the "feels like a friend, minimal" persona Miori wants.
- Some internals only documented via secondary sources — verify before relying.

## 6. What Miori Core should BORROW
- **Backend module decomposition** (auth / db / middleware / llm-core / agent-loop / agent-tools / chat / search) as a blueprint for `services/core-api/app/services/*`.
- **Memory design**: SQLite for structured data + a vector store (Chroma or a lighter SQLite-vec/FAISS option) for semantic recall, with import/export — but make the vector layer **lazy-loaded/optional** per Miori's constraint.
- **Model-agnostic provider routing** across local (Ollama/llama.cpp) and cloud (OpenAI/OpenRouter) backends.
- **Scheduled agent tasks** (cron-style) + **multi-channel notifications** pattern for the Tasks module.
- **Deep Research loop** (plan → search → read sources → synthesize report) as the Research page's backbone.
- **"Compare" pattern** as an optional power feature (P2).
- **`data/` local-first layout** and 127.0.0.1-by-default security posture.

## 7. What Miori Core should NOT borrow
- **Any AGPL-licensed source code verbatim** — architecture/ideas only.
- The full feature surface (email/IMAP, calendar/CalDAV, image editor, gallery, themes) for v0.1 — defer or drop.
- Mandatory ChromaDB + SearXNG + ntfy stack as always-on dependencies — make them optional.
- The cockpit-style workspace UI aesthetic.
- Docker-Compose-as-the-primary-distribution assumption (Miori is Tauri desktop first).

## 8. Likely integration target inside Miori Core
- Backend service decomposition: `services/core-api/app/services/` (chat, agent-loop)
- Memory (SQLite + optional vector): `services/core-api/app/services/memory/`
- Provider routing: `services/core-api/app/services/providers/`
- Tools / MCP / shell / skills: `services/core-api/app/services/tools/`
- Scheduled tasks + notifications: `services/core-api/app/services/tasks/`
- Deep research: maps to Research page → `apps/desktop/src/features/research/` + a `services/.../research/` (to add)
- Documents/notes: `apps/desktop/src/features/*` (files/tasks) and corresponding services.

## 9. Implementation risk notes
- **License is the dominant risk.** Keep a hard wall: read Odysseus for design, write Miori's own code. Document this provenance to avoid AGPL contamination.
- **Footprint discipline:** adopt the architecture but gate Chroma/SearXNG/heavy model serving behind feature flags so the low-end-machine baseline stays light.
- **Scope control:** the breadth is seductive; explicitly scope v0.1 to Chat/Memory/Tasks/Research skeletons and stub the rest.
- Verify secondary-sourced internals (opencode agent loop, fastembed) against the repo before designing around them.

## 10. Priority level
**P0 (as an architectural template).** Highest-value design reference for the workspace backend, memory, provider routing, and tasks. Note: P0 for *learning from*, not for *copying* — implementation is bounded by the AGPL wall and the v0.1 scope.

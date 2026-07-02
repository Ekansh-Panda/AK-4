# Khoj — Repo Analysis

> Engineering due-diligence for Miori Core. Grounded in the public repo
> `github.com/khoj-ai/khoj` and project docs. Items from secondary write-ups (vs. the
> README/repo) are labelled `[SECONDARY-SOURCE]`; reasoned extrapolations are
> `[INFERRED]`. Confirm exact internals (DB, vector store, embedding model) against
> `pyproject.toml` / `docker-compose.yml` before depending on them.

## 1. What the repo is
Khoj is an open-source, self-hostable "AI second brain": it indexes your personal
documents (PDF, Markdown, Org-mode, Word, Notion, plaintext, images) and lets you ask
questions answered via Retrieval-Augmented Generation (RAG) over that corpus or the
web. It supports custom agents, scheduled automations (newsletters, smart
notifications), deep research, image generation, and speech, and is reachable from
Browser, Obsidian, Emacs, Desktop, Phone, and WhatsApp. It works with online LLMs
(GPT/Claude/Gemini/DeepSeek) and local models via Ollama/llama.cpp. For Miori Core,
Khoj is the **reference design for the personal-knowledge retrieval / second-brain**
layer — i.e. how Miori should index the user's docs and recall them semantically.

## 2. Tech stack
- **Backend:** Python, FastAPI core. `[SECONDARY-SOURCE]`
- **Frontend/clients:** TypeScript web UI; plus Obsidian plugin, Emacs (Emacs Lisp), Desktop, mobile, WhatsApp. (Repo language split: Python ~51%, TypeScript ~36%, Emacs Lisp ~2%.)
- **Retrieval:** semantic search via sentence-transformers embeddings into a vector index; classic RAG (top-k chunks → LLM context). `[SECONDARY-SOURCE]`
- **Models:** online (GPT/Claude/Gemini/DeepSeek/Qwen/Mistral) and local via Ollama/llama.cpp.
- **Capabilities tagged:** `rag`, `semantic-search`, `llm`, `llamacpp`, `offline-llm`, `stt`, `image-generation`.
- **Deployment:** Docker / docker-compose for self-hosting; cloud option available.
- **License:** AGPL-3.0.
- **Backed by:** Y Combinator.

## 3. Standout features
- **RAG over heterogeneous personal docs** (PDF/MD/Org/Word/Notion/images) — broad ingestion.
- **Advanced semantic search** across the whole knowledge base.
- **Custom agents** with their own knowledge, persona, chat model, and tools.
- **Scheduled automations** — recurring research, newsletters, smart notifications to inbox.
- **Deep research** capability.
- **Many access surfaces** (Obsidian/Emacs/Desktop/Phone/WhatsApp) over one backend.
- **Local + offline** operation via Ollama/llama.cpp; STT and image generation.

## 4. Strengths
- **Best-in-class second-brain/RAG architecture** to learn from — exactly the indexing + retrieval Miori's Memory and Research pages need.
- **FastAPI + Python** matches Miori's stack; patterns transfer cleanly.
- **Multi-format ingestion pipeline** is a mature template for Miori's Files → Memory indexing path.
- **Persona-per-agent** concept aligns with Miori's persona system.
- **Local/offline-first** support fits the self-hosted, low-dependency goal.
- **Automations/notifications** overlap with Miori's Tasks module.

## 5. Limitations / weak points
- **AGPL-3.0** — same copyleft constraint as Odysseus; architecture/ideas only, no verbatim code.
- **Heavyweight for low-end machines** — sentence-transformers embeddings + vector index + local model serving need real RAM/GPU; conflicts with Miori's low-end baseline unless lazy-loaded.
- **Breadth of clients** (Obsidian/Emacs/WhatsApp) is out of scope for Miori v0.1.
- **Indexing cost/latency** — large personal corpora need careful incremental indexing; naive re-index is expensive.
- **Exact internal stack (vector DB, embedding model)** is partly secondary-sourced — verify.
- More of a **knowledge tool than a "friend"** — UX ethos differs from Miori's warm companion persona.

## 6. What Miori Core should BORROW
- **RAG retrieval pipeline shape**: ingest → chunk → embed → vector index → top-k retrieve → LLM context. This is the core of Miori's semantic Memory.
- **Multi-format document ingestion** (start with MD/PDF/plaintext; add more later) feeding the index from the Files module.
- **Incremental/lazy indexing** so embedding only runs when needed (honors low-end-machine constraint via lazy-load).
- **Scheduled automations** pattern (recurring agent jobs that produce notifications/digests) for Tasks.
- **Local-first embedding option** (small sentence-transformers or fastembed/ONNX) with a cloud fallback.
- **Per-agent persona+knowledge** concept feeding Miori's persona system.

## 7. What Miori Core should NOT borrow
- **AGPL source code verbatim** — design only.
- The wide client matrix (Obsidian/Emacs/WhatsApp) — Miori is Tauri desktop + remote dashboard.
- Always-on heavy embedding/model serving as a hard dependency — must be optional/lazy.
- WhatsApp/3rd-party messaging integrations for v0.1.
- Any ingestion default that re-indexes the whole corpus eagerly.

## 8. Likely integration target inside Miori Core
- Semantic memory / RAG core: `services/core-api/app/services/memory/`
- Document ingestion (chunk/embed from files): `services/core-api/app/services/files/` → memory pipeline
- Provider/embedding backends (local + cloud): `services/core-api/app/services/providers/`
- Automations / scheduled retrieval jobs: `services/core-api/app/services/tasks/`
- Research surface: `apps/desktop/src/features/research/` + research service (to add)
- Persona-with-knowledge: `services/core-api/app/services/persona/`

## 9. Implementation risk notes
- **License wall** identical to Odysseus — read for design, write Miori's own code, document provenance.
- **Embedding footprint** is the key engineering tension vs. the low-end-machine goal; default to a tiny/quantized local embedder or a cloud embedding API, and gate the heavy path behind a feature flag.
- **Indexing correctness** (chunking strategy, incremental updates, stale-doc invalidation) is where second-brain systems get hard — budget time for the ingestion pipeline, not just retrieval.
- For v0.1, ship a **thin RAG interface + SQLite store stub** and defer real embedding integration.

## 10. Priority level
**P1.** The retrieval/second-brain layer is core to Miori's Memory and Research value, but heavy embeddings push full implementation past v0.1 — deliver clean interfaces now, integrate the real RAG path in a later milestone.

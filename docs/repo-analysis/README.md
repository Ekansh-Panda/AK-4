# Miori Core — Donor Repo Analysis

Engineering due-diligence on the donor repos/categories named in `MISSION.md`, to guide
**selective feature harvesting** for Miori Core (a cross-platform personal AI friend +
workstation + remote-desktop companion). These are **planning documents**: we read
donors for architecture and ideas, then implement Miori's own clean code — per the
mission's hard constraints ("new architecture, not direct repo-merging").

## How to read these
- Each report follows a fixed 10-section structure (summary → tech stack → features →
  strengths → limitations → borrow → don't-borrow → integration target → risk →
  priority).
- The two private **Mark** repos are analyzed from their described archetype; details
  not verifiable from a public source are explicitly labelled `[INFERRED]`.
- Public donors (Odysseus, Khoj, OpenAdapt, LangGraph) are web-grounded; details from
  secondary write-ups (not the repo/README itself) are labelled `[SECONDARY-SOURCE]`.

## Summary table

| Repo / Category | What it is | Representative | License | Primary borrow | Main risk | Integration target | Priority |
|---|---|---|---|---|---|---|---|
| [Mark-XLVI](./mark-xlvi.md) | Jarvis-style desktop assistant: remote control, file transfer, wake/sleep | private donor | n/a (owner) | Wake/sleep lifecycle; remote-command + file-transfer flows; action registry | Insecure remote/file code; OS coupling; cockpit UI | `services/.../remote/`, `services/.../files/`, `apps/remote-dashboard/`, `app/ws/` | **P1** |
| [MARK-XL](./mark-xl.md) | Earlier sibling Mark assistant; minimal core loop | private donor | n/a (owner) | Intent→handler registry; minimal legible loop; low footprint | Superseded; brittle rule routing | `services/.../tools/`, `services/.../providers/`, persona/chat | **P2** |
| [Odysseus](./odysseus.md) | Self-hosted AI workspace: chat/agents, research, docs, notes/tasks, memory, compare | `pewdiepie-archdaemon/odysseus` | AGPL-3.0 | Backend module decomposition; memory (SQLite+vector); provider routing; scheduled tasks; deep research | AGPL copyleft; feature sprawl; heavy footprint | `services/.../` (chat/agent), `memory/`, `providers/`, `tasks/`, `tools/` | **P0 (template)** |
| [Khoj](./khoj.md) | Self-hosted second brain: RAG/semantic search over personal docs, automations | `khoj-ai/khoj` | AGPL-3.0 | RAG pipeline; multi-format ingestion; incremental indexing; local embeddings | AGPL copyleft; embedding footprint; indexing cost | `services/.../memory/`, `files/`→memory, `providers/`, `tasks/`, research | **P1** |
| [Computer-Use / action loop](./computer-use-openadapt-or-similar.md) | VLM-driven observe→act→verify GUI automation with safety gates + HITL | `OpenAdaptAI/OpenAdapt` | MIT | Action-loop contract; safety gate/confirm-mode; HITL fallback; action/audit log | Highest blast radius; VLM cost; cross-platform actuation | `services/.../tools/computer_use/`, `remote/`, `app/ws/`, `models/` | **P2** |
| [Agent orchestration](./agent-orchestration.md) | Stateful graph agent control: checkpointing, HITL, memory, time-travel | `langchain-ai/langgraph` | MIT | Graph/state-machine loop; SQLite checkpointing; HITL interrupts; memory split | Framework weight (LangChain churn); over-engineering | `services/.../orchestration/`, `db/`+`models/`, `app/ws/`, `tools/` | **P1** |

## Cross-cutting takeaways for Miori Core

1. **Stack alignment is strong.** Odysseus and Khoj are both FastAPI + Python + SQLite +
   vector store — the same stack Miori mandates. Adopt their *architecture*, write our
   own code.
2. **License wall.** Odysseus and Khoj are **AGPL-3.0** — read for design only, never
   copy source. OpenAdapt and LangGraph are MIT (reuse legally allowed) but Miori's
   "new architecture" rule still favors clean re-implementation. Document provenance.
3. **HITL + safety gates are the backbone for risky features.** Remote control
   (Mark-XLVI), computer-use (OpenAdapt), and orchestration (LangGraph) all converge on
   the same requirement: approve-before-execute, full audit log, scoped permissions.
   Design this contract early even while execution is stubbed.
4. **Footprint discipline is the recurring tension.** Vector stores (Chroma/sentence-
   transformers), VLM screenshot loops, and LangChain all fight the "low-end machine"
   constraint — gate every heavy path behind optional/lazy-loaded feature flags.
5. **v0.1 = clean interfaces + stubs.** Per the mission's quality bar, the right
   deliverable now is well-shaped interfaces, models, and TODOs in the mapped service
   paths — not full implementations of memory RAG, computer-use, or orchestration.

## Priority rollup
- **P0 (design template):** Odysseus — closest architectural match for the workspace backend.
- **P1 (core, interface-first for v0.1):** Mark-XLVI (remote/files), Khoj (memory/RAG), Agent orchestration (loop + HITL).
- **P2 (later milestones):** MARK-XL (reference only), Computer-use (heavy, high-risk flagship).

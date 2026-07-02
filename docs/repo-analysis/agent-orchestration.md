# Agent Orchestration Category — Repo Analysis (LangGraph as representative)

> Engineering due-diligence for Miori Core. This is a **category** analysis using
> LangGraph (`github.com/langchain-ai/langgraph`) as the representative, well-known
> agent-orchestration project. Grounded in the public repo and docs; secondary
> write-ups are `[SECONDARY-SOURCE]` and reasoned extrapolations `[INFERRED]`.
> Adjacent comparisons in the same category include CrewAI, AutoGen, and OpenAI
> Swarm/Agents SDK — referenced where useful.

## 1. What the repo is
LangGraph is a framework for building stateful, controllable AI agents as **graphs**:
nodes are processing steps, edges are transitions, and a shared typed state object
flows through them with reducers merging updates. It adds cyclic/branching control
flow, durable execution via **checkpointing**, first-class **human-in-the-loop**
(static breakpoints + dynamic node interrupts), short- and long-term **memory**, and
observability (LangSmith). It sits above LangChain components. For Miori Core it is the
reference design for **how to orchestrate the agent loop** — the control plane that
ties together chat, tools, memory, persona, and (eventually) computer-use into
resumable, inspectable, human-approvable workflows.

## 2. Tech stack
- **Language/core:** Python (also a JS/TS implementation) within the LangChain ecosystem.
- **Core abstractions:** `StateGraph`, nodes, edges, typed state (`TypedDict`), reducers (`Annotated[list, operator.add]` for accumulation).
- **Persistence/checkpointers:** `MemorySaver` (dev), `SqliteSaver`, `PostgresSaver`, Redis — pluggable. `[SECONDARY-SOURCE]`
- **HITL:** `interrupt_before` / `interrupt_after` static breakpoints; dynamic `interrupt()` + `Command(resume=...)`; `update_state()` to edit state mid-run.
- **Memory:** short-term (in-thread state) + long-term (cross-session stores).
- **Observability:** LangSmith tracing, time-travel debugging via checkpoint tree.
- **Deployment:** library; pairs with FastAPI for serving HITL agents. `[SECONDARY-SOURCE]`
- **License:** MIT.

## 3. Standout features
- **Stateful graph control flow** — explicit, modifiable, supports loops/branches (beyond linear chains).
- **Durable execution / checkpointing** — state saved after each node; resume from last checkpoint after failure; long-running agents.
- **Human-in-the-loop as a first-class primitive** — pause for approval, edit state, approve/reject tool calls, then resume from the exact checkpoint.
- **Time-travel debugging** — checkpoints form a branching tree (Git-like); inspect/rewind/fork any state.
- **Short- + long-term memory** built into the model.
- **Thread-scoped persistence** via `thread_id` (multi-session).

## 4. Strengths
- **The canonical pattern for resumable, inspectable agent loops** — exactly Miori's need to make agent actions transparent and approvable.
- **Checkpointing maps perfectly to Miori's SQLite default** (`SqliteSaver`) — durable agent state with the mandated DB.
- **HITL is the right safety model** for Miori's risky actions (computer-use, file ops, remote control) — approve before execute.
- **MIT-licensed** — code reuse is legally permissible (though Miori's clean-architecture rule favors a thin own implementation).
- **Provider/tool-agnostic** orchestration composes cleanly over Miori's providers + tools abstractions.
- **Time-travel/observability** is a strong debugging story for a complex companion.

## 5. Limitations / weak points
- **Conceptual weight / learning curve** — graphs, reducers, checkpointers add complexity that can overshoot a v0.1 friend-companion.
- **LangChain ecosystem coupling** `[INFERRED]` — pulling in LangGraph drags LangChain surface area and version churn; heavier dependency than Miori's lean baseline wants.
- **Footprint** — full framework + LangSmith is more than a low-end-machine baseline needs.
- **Opinionated state model** may not fit Miori's WebSocket-streaming chat shape without adaptation.
- **Rapidly evolving API** `[INFERRED]` — interrupt/Command APIs have shifted across versions; pinning required.

## 6. What Miori Core should BORROW
- **Graph/state-machine orchestration concept** for the agent loop — model the chat→reason→tool→observe→respond cycle as explicit nodes/edges with a typed state object, even if Miori implements a thin in-house version rather than importing LangGraph.
- **Checkpointing on SQLite** — persist agent run state per session/`thread_id` so runs are resumable and inspectable (directly compatible with Miori's SQLAlchemy+SQLite).
- **HITL primitives** — interrupt-before-tool (approval gate) and interrupt-after (review results), with state edit + resume. This is the safety backbone for computer-use/remote/file actions.
- **Short- + long-term memory split** mirroring Miori's `memory` module (working memory vs. persisted recall).
- **Time-travel / run-inspection** idea for the Tasks/Research transparency UX.

## 7. What Miori Core should NOT borrow
- The **full LangGraph + LangChain dependency tree** as a hard requirement — prefer a lean in-house orchestration core; gate any heavy framework behind an optional/lazy module if adopted at all.
- **LangSmith** as a required dependency (proprietary cloud) — use lightweight local tracing/logging instead.
- Over-engineering the graph for v0.1 — don't build branching/time-travel before the linear loop works.
- Importing the framework's churny APIs into Miori's stable core without a pin/adapter.

## 8. Likely integration target inside Miori Core
- Agent orchestration / loop engine: `services/core-api/app/services/` (a new `orchestration/` or `agent/` module) coordinating chat + tools + memory + persona
- Checkpointing store: `services/core-api/app/db/` + `services/core-api/app/models/` (run/checkpoint tables on SQLite)
- HITL approval events: `services/core-api/app/ws/` (status/approval channel) + `apps/remote-dashboard/` and `apps/desktop/src/features/remote/`
- Tool execution gating: `services/core-api/app/services/tools/` (esp. `tools/computer_use/`)
- Memory hooks: `services/core-api/app/services/memory/`

## 9. Implementation risk notes
- **Build vs. adopt:** importing LangGraph buys durability/HITL/checkpointing fast but adds LangChain weight and API churn against Miori's lean, low-end-machine goal. Recommendation: **adopt the patterns, implement a thin in-house orchestrator** over SQLite for v0.1; reconsider importing LangGraph only if orchestration complexity grows.
- **HITL is the linchpin** for safely enabling computer-use/remote/file actions — design the approval/interrupt contract early even if execution is stubbed.
- **State model alignment** — ensure the orchestration state cooperates with Miori's WebSocket streaming rather than fighting it.
- Pin versions and wrap any third-party orchestration API behind an adapter to absorb churn.

## 10. Priority level
**P1.** Orchestration is the connective tissue for Miori's agentic features and the safety (HITL) layer that gates the risky tools. v0.1 should ship a clean in-house orchestration interface + SQLite checkpoint stub + HITL contract; full graph/time-travel features are later milestones.

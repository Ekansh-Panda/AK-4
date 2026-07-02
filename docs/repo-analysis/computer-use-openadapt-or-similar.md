# Computer-Use / Action-Loop Category — Repo Analysis (OpenAdapt as representative)

> Engineering due-diligence for Miori Core. This is a **category** analysis using
> OpenAdapt (`github.com/OpenAdaptAI/OpenAdapt`) as the representative, well-known
> "Open Computer Use"-style action-loop project. Grounded in the public repo,
> ecosystem sub-packages, and architecture wiki. Where details come from secondary
> write-ups they are `[SECONDARY-SOURCE]`; reasoned extrapolations are `[INFERRED]`.
> Anthropic's Claude "Computer Use" and similar VLM-driven loops are noted as
> adjacent comparisons in the same category.

## 1. What the repo is
OpenAdapt is open-source "Generative Process Automation" (generative RPA): an adapter
between large multimodal/vision-language models and real desktop & web GUIs. Its core
loop is **Demonstrate → Learn → Execute**: record GUI demonstrations (mouse, keyboard,
screen, window events), then have a VLM generate the *next action* given the current
(marked) screenshot and the current process step, verify completion criteria, and
advance — pausing for human help when stuck. The category as a whole (OpenAdapt,
Claude Computer Use, Open Computer Use agents) defines the pattern Miori needs for its
**desktop computer-use tool**: observe screen → reason → emit action → execute →
re-observe, with safety gates and human-in-the-loop.

## 2. Tech stack
- **Language:** Python; distributed via PyPI (`pip`/`uv`), modular meta-package (v1.0+).
- **Sub-packages:** `openadapt-capture` (GUI capture), `openadapt-ml` (training/inference), `openadapt-agent` (production runtime), `openadapt-grounding` (UI element detection), `openadapt-tray` (confirmation dialogs), `openadapt-evals` (benchmarks), `openadapt-privacy` (PII/PHI scrubbing).
- **Data/storage:** SQLite `recording.db` (events, screenshots, window events, perf), MP4 screen recording (action-gated), optional audio FLAC. `[SECONDARY-SOURCE]`
- **Models:** Qwen2.5-VL / Qwen3-VL backbones; API agents for Claude/GPT; a dedicated `ClaudeComputerUseAgent` (coordinate clamping + fail-safe recovery).
- **ML stack:** TRL + Unsloth for fine-tuning (2x faster, ~50% less VRAM).
- **Config:** `pydantic-settings` (env / `.env`).
- **P2P sharing:** Magic Wormhole.
- **Cloud eval:** Azure/AWS VM managers, SSH tunnels, pool manager.
- **License:** MIT (note: friendlier than Odysseus/Khoj AGPL).
- **Status:** alpha.

## 3. Standout features
- **Explicit action loop** with marked-screenshot prompting and per-step completion checks.
- **Safety Gate** — runtime validation before executing high-risk actions ("confirm mode").
- **Human-in-the-loop recovery** — on failure, start a recording, alert the user, resume after correction (tray-driven).
- **Abstraction Ladder** — literal replay → goal-level automation generalization.
- **Evaluation-driven feedback** — success traces become training data.
- **Structured event/screenshot data model** (`Recording` / `ActionEvent` / `Screenshot` / `WindowEvent`).
- **Grounding** sub-package for UI element detection (reduces VLM ambiguity).
- **MIT-licensed**, modular sub-packages you can adopt à la carte.

## 4. Strengths
- **Clean, well-documented action-loop architecture** — the canonical reference for computer-use.
- **Safety + HITL are first-class**, not afterthoughts — exactly the posture Miori needs for actuating a user's machine.
- **MIT license** permits actual code reuse (unlike the AGPL donors) — though Miori's "new architecture" rule still favors re-implementation.
- **Modular packaging** lets Miori cherry-pick (e.g. grounding, capture data model) without the ML training weight.
- **Provider-agnostic agent interfaces** (Claude/GPT/policy) map to Miori's provider abstraction.
- **Structured recording schema** is a ready blueprint for an action/audit log.

## 5. Limitations / weak points
- **Alpha maturity** — not production-hardened.
- **Heavy ML half** (TRL/Unsloth fine-tuning, Qwen-VL, cloud VM eval) is far beyond Miori's low-end-machine scope — Miori wants the *inference/execute* loop, not the *train* pipeline.
- **VLM cost/latency** — screenshot-per-step multimodal calls are expensive and slow on weak hardware.
- **Cross-platform actuation** still hard (coordinate systems, DPI, OS APIs).
- **Security/safety burden is enormous** — anything that drives the GUI can do real damage; needs strict gating.
- **Process Automation framing** (record/replay workflows) is broader than Miori's "friend does a task on my computer" need.

## 6. What Miori Core should BORROW
- **The action-loop contract**: observe (screenshot + state) → reason (next action) → execute → verify completion → advance/repeat. Define this as Miori's computer-use tool interface.
- **Safety Gate / confirm-mode** for high-risk actions — mandatory before any GUI/file/system actuation.
- **Human-in-the-loop fallback** — pause, surface to the remote dashboard, resume after user input (pairs naturally with the WS status channel and Mark-XLVI's lifecycle states).
- **Structured action/audit log** (`ActionEvent` + screenshot + window context) for transparency and debugging.
- **Provider-agnostic agent interface** (swap Claude/GPT/local VLM behind one boundary).
- **Grounding step** concept (resolve UI targets before acting) to reduce VLM coordinate errors.

## 7. What Miori Core should NOT borrow
- The **ML training stack** (TRL/Unsloth/Qwen fine-tuning, cloud VM eval) — out of scope.
- Always-on **screenshot-per-step VLM** as a default — too heavy for low-end machines; make computer-use an opt-in, lazy-loaded tool.
- Full **record/replay RPA** framing — Miori wants assisted task execution, not enterprise process capture.
- Magic-Wormhole P2P sharing of recordings (not a Miori need).
- Any unconfirmed actuation path — never execute high-risk actions without the safety gate.

## 8. Likely integration target inside Miori Core
- Computer-use tool + action loop: `services/core-api/app/services/tools/computer_use/`
- Safety gate / confirm-mode: within `tools/computer_use/` + surfaced via `services/core-api/app/services/remote/` and `apps/remote-dashboard/`
- Action/audit log model: `services/core-api/app/models/` (+ a tool-events table)
- HITL pause/resume events: `services/core-api/app/ws/` (status) + remote dashboard
- VLM/provider backend: `services/core-api/app/services/providers/`
- Host actuation boundary (cross-platform): a thin host-agent under `services/.../tools/computer_use/`

## 9. Implementation risk notes
- **This is the highest-blast-radius feature in Miori** — it can move the mouse, click, type, and touch files. Safety gate + explicit user confirmation + scoped permissions + full audit log are non-negotiable, and security review is required before enabling.
- **Cost/latency on low-end machines** make screenshot-loop computer-use a poor default; ship it as an optional, lazy-loaded P2 tool with clear UX about what it's doing.
- **Cross-platform actuation** needs a clean abstraction; OpenAdapt's per-OS handling is reference, not portable.
- MIT licensing means selective code reuse is *legally* fine, but the mission's "new architecture, no blind code-dumping" rule still applies — re-implement the loop cleanly.

## 10. Priority level
**P2.** Computer-use is a flagship future capability but is heavy, risky, and beyond the v0.1 bar. For v0.1: define the `tools/computer_use/` interface, the action-log model, and the safety-gate/HITL contract as clean stubs; defer real GUI actuation.

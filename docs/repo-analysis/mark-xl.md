# MARK-XL — Repo Analysis

> Engineering due-diligence for Miori Core. MARK-XL is an earlier sibling of
> Mark-XLVI in the project owner's private "Mark" assistant line and is **not** a
> public, independently documented project. Grounding comes from `MISSION.md`
> ("Mark-XLVI / MARK-XL ... use them for ideas, architecture analysis, and selective
> feature harvesting only"). Details marked `[INFERRED]` are reasoned from the
> "earlier Mark assistant" archetype, not verified from source. Confirm against the
> actual repo before relying on any specific.

## 1. What the repo is
MARK-XL (Mark 40) is an earlier-generation desktop AI assistant in the same
Jarvis-style lineage as Mark-XLVI. As the predecessor, it likely carries a simpler,
more readable core: the foundational wake-word → intent → action → speak loop before
later versions layered on remote control and richer features. Its value to Miori
Core is primarily as a **reference for the minimal, legible assistant core** and as a
comparison point that shows which abstractions held up across the XL → XLVI evolution
(those that survived are the ones worth borrowing).

## 2. Tech stack `[INFERRED]`
Likely a leaner subset of Mark-XLVI's stack:
- **Language:** Python.
- **Speech:** wake-word + `speech_recognition`; TTS via `pyttsx3`.
- **NLP/LLM:** simpler intent routing, possibly rule/keyword based, with an optional LLM backend.
- **System control:** `os` / `subprocess` / `pyautogui` for basic app and file actions.
- **UI:** minimal GUI or console/tray.
- **Storage:** flat files / SQLite for settings and history.

## 3. Standout features
- **Clean core assistant loop** (listen → recognize → route intent → act → respond) — likely simpler and easier to learn from than the more featureful XLVI.
- **Intent routing** mapping utterances/commands to handler functions.
- **Basic local actuation** (open apps, simple file ops).
- **Lightweight footprint** — closer to the mission's "usable on low-end machines" constraint than a heavier later build.

## 4. Strengths
- Smaller surface area makes the *essential* assistant patterns easy to extract.
- Owner-authored — full insight into intent, no license friction.
- A clean intent-router and handler-registry idea maps directly onto Miori's tool/provider abstractions.
- Low resource footprint aligns with Miori's low-end-machine goal.

## 5. Limitations / weak points
- **Superseded** — many capabilities were rebuilt better in Mark-XLVI; XL is reference, not a build base.
- **Likely brittle intent handling** `[INFERRED]` — keyword/rule routing doesn't generalize like LLM tool-calling.
- **No/limited remote + file transfer** vs XLVI (those features matured later).
- **Same security gaps** `[INFERRED]` likely present in any networking it does.
- **OS-specific actuation** undermines cross-platform.
- **Throwaway/legacy UI**, incompatible with the minimal dark UI mandate.

## 6. What Miori Core should BORROW
- **Intent/command router → handler-registry pattern** as the conceptual seed for Miori's tool registry (`services/tools/`) and provider routing.
- **The minimal core loop** as a clarity reference: keep Miori's chat→persona→tool→response path legible and small.
- **Lightweight defaults** — prove the path runs on low-end hardware; defer heavy features to lazy-loaded modules (mission constraint).
- **Lessons from XL→XLVI evolution** — which abstractions survived two generations are the safest to adopt.

## 7. What Miori Core should NOT borrow
- Keyword/rule-based intent routing as the primary mechanism — prefer structured LLM tool-calling.
- Any legacy UI.
- OS-specific hardcoded actuation.
- Superseded subsystems that XLVI already replaced — don't port the older version of a thing twice.

## 8. Likely integration target inside Miori Core
- Tool/handler registry pattern: `services/core-api/app/services/tools/`
- Provider/intent routing: `services/core-api/app/services/providers/`
- Core chat loop reference: `services/core-api/app/services/` (chat) + `services/core-api/app/services/persona/`
- Lightweight/lazy-load discipline: informs `services/core-api/app/core/config.py` feature flags.

## 9. Implementation risk notes
- Treat strictly as **reference**, not a copy source — copying superseded code risks importing patterns XLVI already fixed.
- Resist resurrecting rule-based routing; it won't scale to Miori's agentic ambitions.
- As with all Mark repos, any networking code must be re-secured before reuse.

## 10. Priority level
**P2.** Useful conceptual reference (intent routing, minimal core, low-footprint discipline) but largely superseded by Mark-XLVI; low direct-harvest value for v0.1.

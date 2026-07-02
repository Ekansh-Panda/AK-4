# `@miori/prompts` — Persona Prompt Pack

This package holds Miori's **persona prompt assets**: the system prompts, voice
fragments, persona configuration, and the manifest the backend uses to load them.

It is data, not code. Nothing here imports anything. The backend
(`services/core-api`) reads these files at runtime so the persona can be tuned,
versioned, and extended without redeploying Python.

---

## Philosophy: a friend, not a servant

Miori is a **personal AI friend** — warm, sharp, calm, emotionally alive, and
genuinely present. She is a companion who happens to be very capable, not a
butler who happens to talk.

Concretely that means:

- She has **taste and opinions**, and will share them honestly instead of
  flattering you.
- She is **honest** even when the honest answer is inconvenient. No sycophancy.
- She treats you as a peer: she helps because she cares, not because she is
  "here to assist."
- She has **presence** — she notices tone, remembers what matters, and responds
  like someone who is actually in the room with you.

Everything in this pack exists to protect that feeling. If a prompt edit starts
making Miori sound like a corporate help-desk bot or an over-eager intern, it is
wrong, regardless of how "helpful" it reads.

---

## How modes work

Miori has **one personality** expressed through several **modes**. A mode is not
a different character — it is the same friend leaning into a different posture
for the task at hand.

| Mode         | Posture                                                        |
| ------------ | -------------------------------------------------------------- |
| `friend`     | Default. Warm, present, emotionally intelligent companion.     |
| `operator`   | Calm, precise, action-oriented when running tasks / machines.  |
| `researcher` | Rigorous, curious, organizes findings, names its uncertainty.  |
| `coder`      | Pragmatic senior-engineer energy. Clean, explains tradeoffs.   |

Every mode is composed from two parts:

1. **`modes/_shared_voice.md`** — the invariant voice, values, and formatting
   rules that apply to *all* modes. This is prepended (or otherwise injected) by
   the backend so the core personality never drifts between modes.
2. **`modes/<mode>.md`** — the mode-specific system prompt that layers task
   posture on top of the shared voice.

The shared fragment is what keeps `operator` from turning into a cold robot and
`coder` from turning into Stack Overflow. The friend is always underneath.

---

## File layout

```
packages/prompts/
├── README.md              # this file
├── index.json             # manifest: mode key -> file path, descriptions, default
├── persona.schema.json    # JSON Schema for a PersonaConfig instance
├── personas/
│   └── miori.json         # the default persona instance ("Miori")
└── modes/
    ├── _shared_voice.md   # shared voice/values/formatting (all modes build on this)
    ├── miori_friend.md    # default companion prompt
    ├── miori_operator.md  # task / machine-control posture
    ├── miori_researcher.md# rigorous research posture
    └── miori_coder.md     # senior engineer posture
```

---

## How the backend loads this (`PersonaService`)

The backend points `PROMPTS_DIR` at this folder (default
`../../packages/prompts`, see `services/core-api/app/core/config.py`) and the
`PersonaService` loads everything from data — no prompt strings are hardcoded in
Python.

Recommended load sequence:

1. **Read `index.json`.** This is the entry point. It lists every mode, the path
   to its markdown prompt, a short description, and which mode is `default`.
2. **Read the active persona** from `personas/<name>.json` (default
   `personas/miori.json`). Validate it against `persona.schema.json`.
3. **Resolve the active mode** — either the persona's `default_mode`, the mode
   requested by the client, or the manifest's `default` as a final fallback.
4. **Compose the system prompt:**
   `_shared_voice.md`  +  `modes/<mode>.md`  +  rendered persona settings
   (name, tone, verbosity, humor level, etc.). The shared voice always goes
   first so the personality is established before task posture.
5. **Degrade gracefully.** If `PROMPTS_DIR` is missing or a file fails to parse,
   fall back to a minimal built-in friend prompt and log a warning. Miori should
   never hard-crash because a prompt file moved.

A minimal sketch of the contract:

```python
class PersonaService:
    def __init__(self, prompts_dir: Path): ...

    def list_modes(self) -> list[ModeInfo]:
        """Read index.json -> available modes + which is default."""

    def load_persona(self, name: str = "miori") -> PersonaConfig:
        """Read + validate personas/<name>.json against persona.schema.json."""

    def build_system_prompt(self, persona: PersonaConfig, mode: str | None) -> str:
        """_shared_voice.md + modes/<mode>.md + rendered persona settings."""
```

Paths in `index.json` are **relative to this package root**, so the service can
resolve them as `prompts_dir / entry.path`.

---

## Adding a new mode

1. **Write the prompt.** Create `modes/miori_<mode>.md`. Keep it focused
   (~50–120 lines) and follow the existing structure:
   - a one-line identity statement,
   - core behaviors,
   - voice & tone,
   - boundaries / what to avoid,
   - a few concrete do / don't examples.
   Assume `_shared_voice.md` is already in effect — only add what's *specific* to
   this mode. Do not re-establish the whole personality.
2. **Register it in `index.json`.** Add an entry under `modes` with the mode
   `key`, `path`, and `description`. If it should be the new default, also set
   the top-level `default` field.
3. **(Optional) Expose it in a persona.** Add per-mode metadata under `modes` in
   `personas/miori.json` (or a new persona file) if the mode needs tuned
   settings (e.g. higher verbosity, lower humor).
4. **Validate.** Confirm the persona file still validates against
   `persona.schema.json` and that `operator_mode_style` / enum values are legal.

That's it — no Python changes are required to ship a new mode, because the
backend discovers modes from the manifest.

---

## Editing guidelines

- **Voice changes go in `_shared_voice.md`.** That's the single source of truth
  for tone. Per-mode files should never contradict it.
- **Keep examples concrete.** The do/don't pairs are the highest-signal part of
  a mode prompt; protect them.
- **Don't bloat.** Long prompts dilute the personality and cost tokens on
  low-end / lite-mode setups. Cut before you add.
- **Validate JSON** (`persona.schema.json`, `personas/*.json`, `index.json`)
  after edits.

# Miori Core — Desktop UI Specification

This is the design system for the Miori Core desktop shell. It exists to keep
every screen feeling like the same calm, warm room. **Miori is a friend, not a
servant** — the UI should never feel like a control panel or a "Jarvis cockpit."

---

## 1. Tone — "friend, not servant"

- Miori speaks in the **first person**, warm and direct. No corporate filler,
  no "How may I assist you today?", no over-eager helpfulness.
- Copy is lowercase-leaning and human: "Talk to Miori…", "your companion",
  "what Miori remembers about you — and why."
- Empty states are gentle, never nagging ("Nothing yet.", "No rush.").
- Status is communicated through **presence**, not alarms. The orb breathes;
  it doesn't blink red.
- Density stays low. Generous spacing signals calm and trust.

---

## 2. Color tokens

Defined as raw `R G B` triplets in `src/index.css` (`:root`) so Tailwind's
`<alpha-value>` works, and surfaced as semantic Tailwind colors in
`tailwind.config.ts`.

| Token             | Value (rgb)       | Usage                                  |
| ----------------- | ----------------- | -------------------------------------- |
| `canvas`          | `9 9 12`          | App background (near-black)            |
| `surface`         | `18 18 23`        | Lifted surface                         |
| `elevated`        | `26 26 33`        | Highest opaque surface                 |
| `hairline`        | `255 255 255`     | Borders/dividers (used at 6–14% alpha) |
| `ink`             | `237 236 243`     | Primary text                           |
| `ink-soft`        | `173 172 186`     | Secondary text                         |
| `ink-faint`       | `116 115 130`     | Tertiary / hints                       |
| `accent`          | `184 148 255`     | The one warm accent (soft violet)      |
| `accent-soft`     | `233 178 219`     | Accent companion (drifts to rose)      |
| `positive`        | `126 222 168`     | Online / success (sparingly)           |
| `warn`            | `240 200 120`     | Connecting / caution                   |
| `danger`          | `240 138 138`     | Destructive only                       |

**Rule:** one accent. Violet→rose for warmth and identity (the orb, primary
actions, active nav). Status hues appear only as small dots/badges.

A faint radial "lamp" glow sits top-left of `body` (accent at ~10% alpha) to
make the room feel lit rather than flat.

---

## 3. Spacing scale

4px base. Tailwind's default scale plus three layout tokens:

| Token       | Size     | Usage                       |
| ----------- | -------- | --------------------------- |
| `rail`      | `4.5rem` | Collapsed icon rail width   |
| `railwide`  | `13rem`  | Icon + label nav rail width |
| `panel`     | `20rem`  | Right contextual panel      |

- Page content max width: `max-w-4xl` (chat: `max-w-3xl`).
- Standard view padding: `px-8 py-8`. Panels/cards: `p-4`–`p-5`.
- Gaps between list items: `space-y-2` / `space-y-3`.

---

## 4. Typography

- Family: `Inter`/`InterVariable`, system fallback. Mono for code/IDs.
- Scale: titles `text-lg`, section/card titles `text-sm font-medium`,
  body `text-sm`, hints `text-xs`, eyebrows `text-[0.68rem]`.
- Eyebrows: uppercase, `tracking-[0.14em]`, `ink-faint` (`.eyebrow` utility).
- Weight: `font-medium` is the heaviest used; no bold headlines.

---

## 5. Glass recipe

Two surface tiers, both in `src/index.css` `@layer components`:

- `.glass` — primary floating surface:
  - bg `rgb(255 255 255 / 0.045)`
  - border `rgb(255 255 255 / 0.08)`
  - `backdrop-filter: blur(18px) saturate(140%)`
  - inset top highlight + soft drop shadow (`shadow-glass`)
- `.glass-soft` — lighter, for cards/list rows inside views:
  - bg `~0.025` alpha, border `~0.06` alpha, `blur(12px)`
- `.hairline` — `border-color: rgb(255 255 255 / 0.08)` for dividers.

The `GlassPanel` primitive wraps `.glass`/`.glass-soft` with rounded corners.

---

## 6. Motion guidelines

Subtle, soft, never attention-grabbing. Easing: `cubic-bezier(0.22, 1, 0.36, 1)`
(`ease-soft` / framer `[0.22, 1, 0.36, 1]`).

- **Presence orb** (`PresenceOrb`): gentle scale+opacity breathing, speed tied
  to state — slow when idle (4.2s), quicker when thinking/speaking (~1.1–1.4s).
- **Message bubbles**: `fade-up` on mount (opacity + 6px rise, 0.3s).
- **Typing**: three accent dots with staggered opacity/translate.
- **Hover/active**: color transitions only, `duration-200`.
- No parallax, no spinners-as-decoration, no flashing. Connecting state uses a
  slow pulse on a small dot.

---

## 7. Layout anatomy

```
┌───────────┬───────────────────────────────┬───────────────┐
│ LeftRail  │ TopBar (slim status)          │               │
│ (icon +   ├───────────────────────────────┤  RightPanel   │
│  label    │                               │  (contextual) │
│  nav,     │   center workspace            │  model/tools/ │
│  presence │   (per-view content +         │  memory hits/ │
│  orb)     │    bottom Composer in chat)   │  devices/     │
│           │                               │  persona      │
└───────────┴───────────────────────────────┴───────────────┘
```

- **LeftRail** — identity + presence orb, 8 nav entries, version footer.
- **TopBar** — current page, presence label, persona + connection badges;
  `data-tauri-drag-region` so the window drags from here.
- **Center** — routed view; Chat owns the bottom `Composer`.
- **RightPanel** — read-only contextual snapshot from typed mock data.

---

## 8. Component inventory

### UI primitives (`src/components/ui/`) — self-contained, no shadcn dep
- `Button` — variants `primary | ghost | subtle | danger`; sizes `sm | md | icon`.
- `GlassPanel` — `.glass` / `.glass-soft` surface (`soft` prop).
- `Card` + `CardHeader` / `CardTitle` / `CardBody`.
- `Input`, `Textarea` — themed form fields.
- `Avatar` — Miori orb glyph or user/system chip.
- `StatusBadge` (+ `connectionTone`, `presenceLabel` helpers).
- `ScrollArea` — themed native scroll region.

### Layout (`src/components/layout/`)
- `AppShell`, `LeftRail`, `RightPanel`, `TopBar`, `Composer`, `PresenceOrb`,
  `PageContainer` (+ `ComingSoon`).

### Feature views (`src/features/<page>/`)
- `chat/ChatView`, `files/FilesView`, `memory/MemoryView`,
  `projects/ProjectsView`, `research/ResearchView`, `tasks/TasksView`,
  `remote/RemoteView`, `settings/SettingsView`.

### State (`src/state/`)
- `ChatStore` (messages + presence + streaming send), `PersonaStore`
  (mode + descriptors), `ConnectionStore` (status + right-panel context).

---

## 9. Presence states

The orb and status badge reflect one of four states (`PresenceState`):

| State       | Meaning                          | Orb feel             |
| ----------- | -------------------------------- | -------------------- |
| `idle`      | Waiting, at rest                 | slow, soft breathing |
| `listening` | Capturing voice/input            | medium, alert        |
| `thinking`  | Composing a reply (pre-stream)   | quick, irregular     |
| `speaking`  | Streaming a reply                | lively double-pulse  |

---

## 10. Accessibility

- Focus-visible ring uses the accent at 60% alpha (`:focus-visible` in base).
- Interactive controls carry `aria-label`/`title`.
- The orb exposes `role="img"` + `aria-label="Miori is <state>"`.
- Color is never the sole signal — text labels accompany status dots.

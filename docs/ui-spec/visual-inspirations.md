# Miori Core — Visual & Identity Direction

> Miori must feel like a **friend, not a cockpit**. This document is the design north star for
> both `apps/desktop` and `apps/remote-dashboard`, and the shared design system in `packages/ui`.
>
> Related: [System Overview](../architecture/system-overview.md) · [Feature Matrix](../feature-matrix.md) · [TASKS.md](../../TASKS.md)

---

## ⚠ Reference-image placeholder (reconcile later)

The user mentioned a **UI reference image** that was **not available** to this overnight build.
Everything below is the **textual design contract** derived from MISSION.md. When the reference
image becomes available:

> **TODO(reconcile-with-image):** Compare these rules against the provided reference image.
> Where the image and these rules disagree, the **image wins** for visual specifics
> (exact palette, orb shape, layout proportions). Update this file and `packages/ui` tokens,
> then remove this placeholder. Do **not** silently diverge — record the diffs here.

---

## 1. Identity in one line

**Miori is a calm, present friend who happens to be powerful.** The UI should read as *a companion you talk to*, not *a console you operate*.

## 2. Mood: dark, glassy, minimal

- **Dark-first.** Deep near-black canvas, never pure `#000`. Content floats on subtle elevated surfaces.
- **Glassy.** Frosted/translucent panels (low-opacity fills + soft blur) for the chrome (sidebar, status bar, cards). Used sparingly so it stays light on GPUs.
- **Minimal.** Generous negative space; one primary action per view; hide complexity until asked. No dense dashboards, no gauge grids, no "Iron Man HUD."

## 3. Friend-not-cockpit principles

| Do | Don't |
|---|---|
| One focal conversation, calm periphery | Wall of panels / telemetry |
| Soft presence cues (the orb breathes) | Blinking alerts, beeping status |
| Warm, human microcopy | Robotic "SYSTEM READY" voice |
| Progressive disclosure | Everything visible at once |
| Quiet when idle | Constant motion / always-on 3D |

## 4. The presence orb

A single living element representing Miori's presence (referenced in [feature matrix](../feature-matrix.md)).

- **One orb, one place** (near chat input / corner). It is identity, not decoration — never more than one.
- **States:** `idle` (slow breathing glow), `listening` (gentle pulse), `thinking` (soft shimmer/rotation), `speaking` (amplitude-reactive), `error` (muted desaturation — never harsh red flash).
- **Cheap to render:** CSS transforms + opacity + a single soft radial gradient. **No WebGL/Three.js in baseline** (low-end rule). A richer 3D orb is an opt-in P2 enhancement, gated behind a setting.
- Implementation target: `apps/desktop/src/components/PresenceOrb` consuming `/ws/status` state.

## 5. Color & spacing direction

> Exact values to be finalized against the reference image; these are the working defaults living in `packages/ui` + `tailwind.config.ts`.

- **Canvas:** very dark neutral (e.g. `#0B0C0F`–`#101216`), slightly cool.
- **Surfaces:** translucent white at low alpha over canvas (glass), with a 1px hairline border at ~8–12% white.
- **Accent:** a single calm signature hue (cool teal/violet family) for the orb glow + primary actions. **One accent only** — restraint signals calm.
- **Text:** high-contrast off-white for primary, muted gray for secondary; never pure white on pure black.
- **Spacing:** 4px base scale; comfortable 16–24px gutters; cards breathe. Rounded corners (`~12–16px`) for softness.
- **Typography:** one clean humanist sans for UI; slightly larger, relaxed line-height in chat to feel conversational.

## 6. Motion guidelines

- **Subtle, organic, purposeful.** Motion communicates presence and state change — never spectacle.
- **Durations:** micro-interactions 120–200ms; presence breathing 3–5s loops; ease-out for entrances, ease-in-out for ambient.
- **Respect `prefers-reduced-motion`** — fall back to opacity-only or static.
- **Performance budget:** ambient animation must stay near-zero CPU when idle; pause off-screen/background animations. No layout-thrashing animations (animate `transform`/`opacity` only).
- **Streaming chat** reveals tokens smoothly (no jarring reflow); the orb reacts to stream start/stop.

## 7. Inspiration boundary (important)

- **Jarvis / HoloJarvis / 3D HUD projects are visual *vibe* inspiration ONLY** — the *feeling* of a present, intelligent companion. We take **none** of their architecture, no holographic cockpit layouts, no 3D-heavy scenes in the baseline.
- Donor repos (Mark-XLVI, Odysseus, Khoj, computer-use) inform **backend/feature** decisions, not visuals (see [feature matrix](../feature-matrix.md)).
- The litmus test for any UI proposal: *"Does this make Miori feel more like a friend, or more like a machine?"* If the latter, cut it.

## 8. Surfaces this applies to

- `apps/desktop/src/components/layout/` — shell, sidebar, status bar
- `apps/desktop/src/features/*` — the eight pages (Chat, Files, Memory, Projects, Research, Tasks, Remote, Settings)
- `apps/remote-dashboard/` — same identity, lighter footprint
- `packages/ui/` — shared tokens + primitives so both apps stay visually identical

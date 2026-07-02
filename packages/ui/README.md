# @miori/ui

Shared design tokens and small pure helpers for Miori Core.

```ts
import { colors, presenceGradients, cx, radialGradient } from "@miori/ui";
```

- `tokens.ts` — colours, radii, spacing scale, motion timings, presence-orb gradients.
- `index.ts` — re-exports tokens plus `cx()` (className join) and `radialGradient()`.

Component primitives (Button, GlassPanel, etc.) intentionally live **inside each
app** (`apps/desktop/src/components/ui`, `apps/remote-dashboard/src/components`)
so each frontend can evolve them independently. This package is the shared
*token* layer that keeps them visually consistent.

See `packages/config/tailwind.preset.ts` for the Tailwind mirror of these tokens.

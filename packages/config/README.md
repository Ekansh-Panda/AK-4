# @miori/config

Shared build configuration for the Miori Core frontends.

## Contents

| File | Purpose |
| --- | --- |
| `tsconfig.base.json` | Strict base TypeScript config extended by each app's `tsconfig.json`. |
| `tailwind.preset.ts` | The Miori design tokens (colours, radii, shadows, motion) as a Tailwind preset. |

## Usage

**TypeScript** — in an app `tsconfig.json`:

```jsonc
{ "extends": "@miori/config/tsconfig.base.json" }
```

**Tailwind** — in an app `tailwind.config.ts`:

```ts
import preset from "@miori/config/tailwind-preset";
export default { presets: [preset], content: ["./index.html", "./src/**/*.{ts,tsx}"] };
```

The same tokens are mirrored as CSS variables in each app's `index.css` so they
can be used outside of Tailwind utility classes (e.g. in inline styles or the
presence orb gradients).

> Design intent: minimal, dark, glassy, one warm accent. Miori is a friend, not
> a cockpit. See `docs/ui-spec/` for the full rationale.

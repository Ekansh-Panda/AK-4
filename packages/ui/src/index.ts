/**
 * @miori/ui — shared design tokens and tiny style helpers.
 *
 * Component primitives (Button, Card, GlassPanel, ...) live inside each app so
 * they can stay self-contained and framework-versioned. This package exports
 * the cross-app design tokens and a couple of pure helpers.
 */

export * from "./tokens";

/** Conditional className join (no dependency on clsx). */
export function cx(...parts: Array<string | false | null | undefined>): string {
  return parts.filter(Boolean).join(" ");
}

/** Build a radial gradient CSS string from two stops. */
export function radialGradient(from: string, to: string): string {
  return `radial-gradient(circle at 30% 30%, ${from}, ${to})`;
}

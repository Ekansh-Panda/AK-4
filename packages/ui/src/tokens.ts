/**
 * Miori Core — canonical design tokens.
 *
 * These mirror packages/config/tailwind.preset.ts and the CSS variables in each
 * app's index.css. Import them when you need token values in TypeScript (e.g.
 * the presence orb gradient, canvas drawing, or inline styles) rather than as
 * Tailwind classes.
 *
 * Design language: minimal, dark, glassy, one warm accent. Miori is a friend,
 * not a cockpit.
 */

export const colors = {
  base900: "#08080b",
  base800: "#0c0c11",
  base700: "#121219",
  base600: "#181822",
  glass: "rgba(22, 22, 30, 0.55)",
  glassStrong: "rgba(28, 28, 38, 0.72)",
  glassBorder: "rgba(255, 255, 255, 0.08)",
  accent: "#b794f6",
  accentSoft: "#c9b1ff",
  accentDeep: "#8b6fd6",
  accentRose: "#f0a6c4",
  ink: "#ecebf0",
  inkMuted: "#a7a6b4",
  inkFaint: "#6e6d7c",
  online: "#7ee0a8",
  busy: "#f0c674",
  offline: "#6e6d7c",
  error: "#f08a8a",
} as const;

export const radii = {
  md: "0.75rem",
  lg: "1rem",
  xl: "1.25rem",
  pill: "9999px",
} as const;

export const spacingScale = [0, 4, 8, 12, 16, 24, 32, 48, 64] as const;

export const motion = {
  /** Subtle by default — Miori breathes, she doesn't flash. */
  fast: "0.15s ease-out",
  base: "0.25s ease-out",
  slow: "0.4s ease-out",
  orbPulse: "2.8s ease-in-out infinite",
} as const;

/** Presence state -> accent gradient stops for the presence orb. */
export const presenceGradients = {
  idle: [colors.accentDeep, colors.accent],
  listening: [colors.accent, colors.accentSoft],
  thinking: [colors.accent, colors.accentRose],
  speaking: [colors.accentSoft, colors.accentRose],
  offline: [colors.offline, colors.base600],
} as const;

export type PresenceKey = keyof typeof presenceGradients;

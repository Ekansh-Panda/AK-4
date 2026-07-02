import type { Config } from "tailwindcss";

/**
 * Miori Core design tokens.
 * Near-black canvas, soft glass surfaces, a single warm violet/rose accent.
 * Keep it calm: this is a friend's room, not a control panel.
 */
export default {
  darkMode: "class",
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        // Surfaces — near-black, layered.
        canvas: "rgb(var(--mi-canvas) / <alpha-value>)",
        surface: "rgb(var(--mi-surface) / <alpha-value>)",
        elevated: "rgb(var(--mi-elevated) / <alpha-value>)",
        // Glass border + hairline.
        hairline: "rgb(var(--mi-hairline) / <alpha-value>)",
        // Text.
        ink: "rgb(var(--mi-ink) / <alpha-value>)",
        "ink-soft": "rgb(var(--mi-ink-soft) / <alpha-value>)",
        "ink-faint": "rgb(var(--mi-ink-faint) / <alpha-value>)",
        // The one warm accent — soft violet/rose.
        accent: "rgb(var(--mi-accent) / <alpha-value>)",
        "accent-soft": "rgb(var(--mi-accent-soft) / <alpha-value>)",
        // Status hues (used sparingly).
        positive: "rgb(var(--mi-positive) / <alpha-value>)",
        warn: "rgb(var(--mi-warn) / <alpha-value>)",
        danger: "rgb(var(--mi-danger) / <alpha-value>)",
      },
      borderRadius: {
        sm: "0.5rem",
        DEFAULT: "0.75rem",
        lg: "1rem",
        xl: "1.25rem",
        "2xl": "1.5rem",
      },
      spacing: {
        // 4px base scale used across the shell.
        rail: "4.5rem",
        railwide: "13rem",
        panel: "20rem",
      },
      fontFamily: {
        sans: [
          "InterVariable",
          "Inter",
          "system-ui",
          "-apple-system",
          "Segoe UI",
          "sans-serif",
        ],
        mono: ["ui-monospace", "SFMono-Regular", "Menlo", "monospace"],
      },
      boxShadow: {
        glass: "0 1px 0 0 rgb(255 255 255 / 0.04) inset, 0 8px 30px -12px rgb(0 0 0 / 0.6)",
        glow: "0 0 24px -4px rgb(var(--mi-accent) / 0.45)",
      },
      backdropBlur: {
        glass: "18px",
      },
      keyframes: {
        "orb-pulse": {
          "0%, 100%": { transform: "scale(1)", opacity: "0.9" },
          "50%": { transform: "scale(1.08)", opacity: "1" },
        },
        "fade-up": {
          "0%": { opacity: "0", transform: "translateY(6px)" },
          "100%": { opacity: "1", transform: "translateY(0)" },
        },
        shimmer: {
          "0%": { backgroundPosition: "-200% 0" },
          "100%": { backgroundPosition: "200% 0" },
        },
      },
      animation: {
        "orb-pulse": "orb-pulse 3.2s ease-in-out infinite",
        "fade-up": "fade-up 0.35s ease-out both",
        shimmer: "shimmer 1.6s linear infinite",
      },
      transitionTimingFunction: {
        soft: "cubic-bezier(0.22, 1, 0.36, 1)",
      },
    },
  },
  plugins: [],
} satisfies Config;

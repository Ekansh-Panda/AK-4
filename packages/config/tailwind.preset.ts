import type { Config } from "tailwindcss";

/**
 * Miori Core — shared Tailwind preset.
 *
 * This is the single source of truth for the Miori visual language:
 * a minimal, dark, glassy aesthetic with one warm accent. Miori is a friend,
 * not a cockpit — spacing is generous, motion is subtle, contrast is calm.
 *
 * Both apps/desktop and apps/remote-dashboard extend this preset so they stay
 * visually consistent. Tokens are also mirrored as CSS variables in each app's
 * index.css (see :root) so they can be referenced outside Tailwind.
 */
const preset: Partial<Config> = {
  darkMode: "class",
  theme: {
    extend: {
      colors: {
        // Near-black layered backgrounds.
        base: {
          900: "#08080b",
          800: "#0c0c11",
          700: "#121219",
          600: "#181822",
        },
        // Soft glass surfaces (use with backdrop blur + low-opacity borders).
        glass: {
          DEFAULT: "rgba(22, 22, 30, 0.55)",
          strong: "rgba(28, 28, 38, 0.72)",
          border: "rgba(255, 255, 255, 0.08)",
        },
        // Warm accent — Miori's presence colour (soft violet drifting to rose).
        accent: {
          DEFAULT: "#b794f6",
          soft: "#c9b1ff",
          deep: "#8b6fd6",
          rose: "#f0a6c4",
        },
        ink: {
          DEFAULT: "#ecebf0",
          muted: "#a7a6b4",
          faint: "#6e6d7c",
        },
        status: {
          online: "#7ee0a8",
          busy: "#f0c674",
          offline: "#6e6d7c",
          error: "#f08a8a",
        },
      },
      borderRadius: {
        xl: "1rem",
        "2xl": "1.25rem",
        "3xl": "1.75rem",
      },
      fontFamily: {
        sans: [
          "Inter",
          "ui-sans-serif",
          "system-ui",
          "-apple-system",
          "Segoe UI",
          "Roboto",
          "Helvetica Neue",
          "Arial",
          "sans-serif",
        ],
        mono: ["JetBrains Mono", "ui-monospace", "SFMono-Regular", "monospace"],
      },
      boxShadow: {
        glass: "0 8px 32px rgba(0, 0, 0, 0.45)",
        glow: "0 0 24px rgba(183, 148, 246, 0.35)",
      },
      backdropBlur: {
        glass: "16px",
      },
      keyframes: {
        "orb-pulse": {
          "0%, 100%": { transform: "scale(1)", opacity: "0.85" },
          "50%": { transform: "scale(1.08)", opacity: "1" },
        },
        "fade-in": {
          from: { opacity: "0", transform: "translateY(4px)" },
          to: { opacity: "1", transform: "translateY(0)" },
        },
        shimmer: {
          "0%": { backgroundPosition: "-200% 0" },
          "100%": { backgroundPosition: "200% 0" },
        },
      },
      animation: {
        "orb-pulse": "orb-pulse 2.8s ease-in-out infinite",
        "fade-in": "fade-in 0.25s ease-out",
        shimmer: "shimmer 1.6s linear infinite",
      },
    },
  },
};

export default preset;

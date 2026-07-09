import { motion } from "framer-motion";
import { useEffect, useState } from "react";
import { cn } from "@/lib/cn";
import type { PresenceState } from "@/lib/types";

export interface PresenceOrbProps {
  state: PresenceState;
  size?: number;
  className?: string;
}

const tuning: Record<
  PresenceState,
  { scale: number[]; opacity: number[]; duration: number; ring: string; core: string }
> = {
  idle: { scale: [1, 1.04, 1], opacity: [0.8, 0.95, 0.8], duration: 4.2, ring: "ring-accent/20", core: "from-accent to-accent-soft" },
  listening: { scale: [1, 1.1, 1], opacity: [0.85, 1, 0.85], duration: 2.2, ring: "ring-accent/40", core: "from-accent to-accent-soft" },
  thinking: { scale: [1, 1.06, 0.98, 1], opacity: [0.7, 1, 0.8, 0.7], duration: 1.4, ring: "ring-accent/30", core: "from-accent to-accent-soft" },
  speaking: { scale: [1, 1.14, 1.02, 1.14, 1], opacity: [0.9, 1, 0.9, 1, 0.9], duration: 1.1, ring: "ring-accent-soft/50", core: "from-accent to-accent-soft" },
  error: { scale: [1, 1.02, 1], opacity: [0.35, 0.5, 0.35], duration: 3.5, ring: "ring-ink-faint/20", core: "from-ink-faint to-ink-faint/60" },
};

export function PresenceOrb({ state, size = 40, className }: PresenceOrbProps) {
  const [reducedMotion, setReducedMotion] = useState(false);
  const t = tuning[state];

  useEffect(() => {
    const mq = window.matchMedia("(prefers-reduced-motion: reduce)");
    setReducedMotion(mq.matches);
    const handler = (e: MediaQueryListEvent) => setReducedMotion(e.matches);
    mq.addEventListener("change", handler);
    return () => mq.removeEventListener("change", handler);
  }, []);

  const coreAnimate = reducedMotion
    ? { scale: 1, opacity: state === "error" ? 0.45 : 0.85 }
    : { scale: t.scale, opacity: t.opacity };
  const coreTransition = reducedMotion
    ? { duration: 0 }
    : { duration: t.duration, repeat: Infinity, ease: "easeInOut" };

  const haloAnimate = reducedMotion
    ? { scale: 1, opacity: 0.5 }
    : { scale: t.scale, opacity: t.opacity.map((o) => o * 0.6) };
  const haloTransition = reducedMotion
    ? { duration: 0 }
    : { duration: t.duration, repeat: Infinity, ease: "easeInOut" };

  return (
    <div
      className={cn("relative grid place-items-center", className)}
      style={{ width: size, height: size }}
      aria-label={`Miori is ${state}`}
      role="img"
    >
      <motion.span
        className="absolute inset-0 rounded-full bg-accent/30 blur-md"
        animate={haloAnimate}
        transition={haloTransition}
      />
      <motion.span
        className={cn(
          "relative rounded-full bg-gradient-to-br",
          t.core,
          "ring-1",
          t.ring,
        )}
        style={{ width: size * 0.55, height: size * 0.55 }}
        animate={coreAnimate}
        transition={coreTransition}
      />
    </div>
  );
}

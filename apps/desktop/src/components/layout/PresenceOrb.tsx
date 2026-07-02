import { motion } from "framer-motion";
import { cn } from "@/lib/cn";
import type { PresenceState } from "@/lib/types";

export interface PresenceOrbProps {
  state: PresenceState;
  size?: number;
  className?: string;
}

/** Tuning per presence state — kept gentle on purpose. */
const tuning: Record<
  PresenceState,
  { scale: number[]; opacity: number[]; duration: number; ring: string }
> = {
  idle: { scale: [1, 1.04, 1], opacity: [0.8, 0.95, 0.8], duration: 4.2, ring: "ring-accent/20" },
  listening: { scale: [1, 1.1, 1], opacity: [0.85, 1, 0.85], duration: 2.2, ring: "ring-accent/40" },
  thinking: { scale: [1, 1.06, 0.98, 1], opacity: [0.7, 1, 0.8, 0.7], duration: 1.4, ring: "ring-accent/30" },
  speaking: { scale: [1, 1.14, 1.02, 1.14, 1], opacity: [0.9, 1, 0.9, 1, 0.9], duration: 1.1, ring: "ring-accent-soft/50" },
};

/**
 * Miori's presence orb. A soft warm sphere that breathes differently depending
 * on what she's doing. This is the heart of the "friend" feeling.
 */
export function PresenceOrb({ state, size = 40, className }: PresenceOrbProps) {
  const t = tuning[state];
  return (
    <div
      className={cn("relative grid place-items-center", className)}
      style={{ width: size, height: size }}
      aria-label={`Miori is ${state}`}
      role="img"
    >
      {/* soft halo */}
      <motion.span
        className="absolute inset-0 rounded-full bg-accent/30 blur-md"
        animate={{ scale: t.scale, opacity: t.opacity.map((o) => o * 0.6) }}
        transition={{ duration: t.duration, repeat: Infinity, ease: "easeInOut" }}
      />
      {/* core */}
      <motion.span
        className={cn(
          "relative rounded-full bg-gradient-to-br from-accent to-accent-soft",
          "ring-1",
          t.ring,
        )}
        style={{ width: size * 0.55, height: size * 0.55 }}
        animate={{ scale: t.scale, opacity: t.opacity }}
        transition={{ duration: t.duration, repeat: Infinity, ease: "easeInOut" }}
      />
    </div>
  );
}

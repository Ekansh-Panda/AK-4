import { cn } from "@/lib/cn";

type Mood = "awake" | "thinking" | "sleeping";

interface PresenceOrbProps {
  mood?: Mood;
  /** Tailwind size classes, e.g. "h-24 w-24". */
  size?: string;
  className?: string;
}

/**
 * Miori's presence orb — a soft, breathing light that stands in for her being
 * "here". Calm by default; quickens a little when thinking; dims when the host
 * is asleep. This is the emotional anchor of the dashboard.
 */
export function PresenceOrb({
  mood = "awake",
  size = "h-24 w-24",
  className,
}: PresenceOrbProps) {
  const sleeping = mood === "sleeping";
  const thinking = mood === "thinking";

  return (
    <div className={cn("relative grid place-items-center", size, className)}>
      {/* Outer halo */}
      <div
        className={cn(
          "absolute inset-0 rounded-full blur-2xl transition-opacity duration-700",
          sleeping ? "bg-ink-faint/20 opacity-40" : "bg-accent/35",
          !sleeping && "animate-orb-pulse",
        )}
      />
      {/* Mid glow */}
      <div
        className={cn(
          "absolute inset-[18%] rounded-full blur-md transition-colors duration-700",
          sleeping ? "bg-ink-faint/25" : "bg-accent/50",
          thinking && "animate-orb-pulse",
        )}
      />
      {/* Core */}
      <div
        className={cn(
          "relative rounded-full transition-all duration-700",
          "h-[42%] w-[42%]",
          sleeping
            ? "bg-gradient-to-br from-ink-faint/70 to-ink-faint/30"
            : "bg-gradient-to-br from-accent-soft to-accent shadow-glow",
        )}
      >
        <span className="absolute left-[22%] top-[18%] h-1/3 w-1/3 rounded-full bg-white/40 blur-[2px]" />
      </div>
    </div>
  );
}

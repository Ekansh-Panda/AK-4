import { cn } from "@/lib/cn";

type Tone = "positive" | "warn" | "danger" | "idle";

interface StatusDotProps {
  tone: Tone;
  /** Soft pulsing halo — use for "live" states. */
  pulse?: boolean;
  className?: string;
}

const TONE: Record<Tone, string> = {
  positive: "bg-positive",
  warn: "bg-warn",
  danger: "bg-danger",
  idle: "bg-ink-faint",
};

/** A small colored status indicator with an optional pulsing halo. */
export function StatusDot({ tone, pulse = false, className }: StatusDotProps) {
  return (
    <span className={cn("relative inline-flex h-2.5 w-2.5", className)}>
      {pulse && (
        <span
          className={cn(
            "absolute inline-flex h-full w-full rounded-full opacity-60 animate-ping",
            TONE[tone],
          )}
        />
      )}
      <span
        className={cn("relative inline-flex h-2.5 w-2.5 rounded-full", TONE[tone])}
      />
    </span>
  );
}

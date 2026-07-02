import { cn } from "@/lib/cn";
import type { ConnectionStatus, PresenceState } from "@/lib/types";

type Tone = "positive" | "warn" | "danger" | "accent" | "muted";

const toneDot: Record<Tone, string> = {
  positive: "bg-positive",
  warn: "bg-warn",
  danger: "bg-danger",
  accent: "bg-accent",
  muted: "bg-ink-faint",
};

export interface StatusBadgeProps {
  label: string;
  tone?: Tone;
  pulse?: boolean;
  className?: string;
}

export function StatusBadge({ label, tone = "muted", pulse, className }: StatusBadgeProps) {
  return (
    <span
      className={cn(
        "inline-flex items-center gap-1.5 rounded-full px-2.5 py-1",
        "text-[0.7rem] font-medium text-ink-soft glass-soft",
        className,
      )}
    >
      <span className={cn("h-1.5 w-1.5 rounded-full", toneDot[tone], pulse && "animate-orb-pulse")} />
      {label}
    </span>
  );
}

/** Map connection status to a badge tone + label. */
export function connectionTone(status: ConnectionStatus): { tone: Tone; label: string } {
  switch (status) {
    case "connected":
      return { tone: "positive", label: "Connected" };
    case "connecting":
      return { tone: "warn", label: "Connecting" };
    default:
      return { tone: "muted", label: "Offline · mocks" };
  }
}

/** Map presence to a label for the status bar. */
export function presenceLabel(p: PresenceState): string {
  return { idle: "Idle", listening: "Listening", thinking: "Thinking", speaking: "Speaking" }[p];
}

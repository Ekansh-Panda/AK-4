import { cn } from "@/lib/cn";
import { useConnection } from "@/state/connection";
import type { ConnectionStatus } from "@/lib/types";
import { StatusDot } from "./StatusDot";

const LABEL: Record<ConnectionStatus, string> = {
  connected: "Connected",
  connecting: "Connecting…",
  disconnected: "Offline",
  error: "Can't reach host",
};

const TONE: Record<ConnectionStatus, "positive" | "warn" | "danger" | "idle"> = {
  connected: "positive",
  connecting: "warn",
  disconnected: "idle",
  error: "danger",
};

/**
 * Persistent header chip showing the live connection state. Pulls from the
 * connection context so it stays accurate everywhere it's mounted.
 */
export function ConnectionChip({ className }: { className?: string }) {
  const { status, hostName, host } = useConnection();
  const tone = TONE[status];
  const detail =
    status === "connected" ? (hostName ?? host) : LABEL[status];

  return (
    <div
      className={cn(
        "inline-flex items-center gap-2 rounded-full border border-white/[0.08]",
        "bg-white/[0.04] px-3 py-1.5 text-xs text-ink-soft backdrop-blur-glass",
        className,
      )}
      role="status"
      aria-live="polite"
    >
      <StatusDot
        tone={tone}
        pulse={status === "connected" || status === "connecting"}
      />
      <span className="max-w-[8.5rem] truncate font-medium text-ink">
        {LABEL[status]}
      </span>
      {status === "connected" && detail && (
        <span className="max-w-[7rem] truncate text-ink-faint">· {detail}</span>
      )}
    </div>
  );
}

import type { PlanStatus, PlanStepStatus } from "@/lib/types";

type Tone = "positive" | "warn" | "danger" | "accent" | "muted";

/** Map a plan status to a StatusBadge tone. */
export function planTone(status: string): Tone {
  switch (status as PlanStatus) {
    case "completed":
      return "positive";
    case "running":
      return "accent";
    case "pending":
      return "warn";
    case "failed":
    case "rejected":
      return "danger";
    case "cancelled":
      return "muted";
    default:
      return "muted";
  }
}

/** Map a step status to a StatusBadge tone. */
export function stepTone(status: string): Tone {
  switch (status as PlanStepStatus) {
    case "completed":
      return "positive";
    case "running":
      return "accent";
    case "pending":
      return "muted";
    case "pending_approval":
      return "warn";
    case "failed":
    case "rejected":
      return "danger";
    default:
      return "muted";
  }
}

/** Derive a ws:// status URL from the configured API base (matches PresenceStore). */
export function statusWsUrl(): string {
  const explicit = import.meta.env.VITE_MIORI_WS_STATUS as string | undefined;
  if (explicit) return explicit;
  const apiBase =
    (import.meta.env.VITE_MIORI_API as string | undefined) ??
    "http://localhost:8000/api";
  const origin = apiBase.replace(/\/api\/?$/, "");
  return origin.replace(/^http/, "ws") + "/ws/status";
}

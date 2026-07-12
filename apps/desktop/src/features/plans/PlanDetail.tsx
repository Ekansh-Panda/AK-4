import { useCallback, useEffect, useRef, useState } from "react";
import {
  ArrowLeft,
  Check,
  X,
  RotateCcw,
  Image as ImageIcon,
  GitBranch,
} from "lucide-react";
import { GlassPanel } from "@/components/ui/GlassPanel";
import { Button } from "@/components/ui/Button";
import { StatusBadge } from "@/components/ui/StatusBadge";
import { ScrollArea } from "@/components/ui/ScrollArea";
import { api, apiOrigin } from "@/lib/api";
import { cn } from "@/lib/cn";
import type { ApiPlan, ApiPlanDetail, ApiPlanStep } from "@/lib/types";
import { planTone, stepTone, statusWsUrl } from "./planStatus";

interface PlanDetailProps {
  planId: string;
  onBack: () => void;
}

/** Parse a step's args_json and return the referenced sub-plan id, if any. */
function subPlanIdOf(step: ApiPlanStep): string | null {
  if (!step.args_json) return null;
  try {
    const parsed = JSON.parse(step.args_json) as Record<string, unknown>;
    const id = parsed?.sub_plan_id;
    return typeof id === "string" ? id : null;
  } catch {
    return null;
  }
}

export function PlanDetail({ planId, onBack }: PlanDetailProps) {
  const [plan, setPlan] = useState<ApiPlanDetail | null>(null);
  const [subPlans, setSubPlans] = useState<ApiPlan[]>([]);
  const [offline, setOffline] = useState(false);
  const [busyStep, setBusyStep] = useState<string | null>(null);
  const [logs, setLogs] = useState<string[]>([]);
  const wsRef = useRef<WebSocket | null>(null);
  const closedRef = useRef(false);

  const load = useCallback(async () => {
    const r = await api.getPlan(planId);
    setOffline(!r.ok);
    if (r.ok && r.data) {
      setPlan(r.data);
      // Resolve any sub-plans referenced by steps.
      const subIds = r.data.steps
        .map(subPlanIdOf)
        .filter((x): x is string => Boolean(x));
      if (subIds.length) {
        const results = await Promise.all(subIds.map((id) => api.getPlan(id)));
        setSubPlans(
          results
            .filter((res) => res.ok && res.data)
            .map((res) => res.data as ApiPlan),
        );
      } else {
        setSubPlans([]);
      }
    }
  }, [planId]);

  useEffect(() => {
    void load();
  }, [load]);

  // Live updates: subscribe to /ws/status and refetch when this plan changes.
  useEffect(() => {
    closedRef.current = false;
    const connect = () => {
      if (closedRef.current) return;
      let ws: WebSocket;
      try {
        ws = new WebSocket(statusWsUrl());
      } catch {
        return;
      }
      wsRef.current = ws;
      ws.onmessage = (ev) => {
        try {
          const data = JSON.parse(ev.data as string) as Record<string, unknown>;
          const type = String(data.type ?? "");
          if (type === "heartbeat") return;
          const pid = data.plan_id ?? data.sub_plan_id;
          if (pid === planId || type.startsWith("plan") || type.startsWith("step") || type.startsWith("subplan")) {
            setLogs((prev) => [
              `${new Date().toLocaleTimeString()} · ${type}`,
              ...prev,
            ].slice(0, 50));
            if (pid === planId || type === "subplan_created") void load();
          }
        } catch {
          /* ignore malformed frames */
        }
      };
      ws.onclose = () => {
        wsRef.current = null;
        if (!closedRef.current) setTimeout(connect, 3000);
      };
      ws.onerror = () => {
        try {
          ws.close();
        } catch {
          /* noop */
        }
      };
    };
    connect();
    return () => {
      closedRef.current = true;
      try {
        wsRef.current?.close();
      } catch {
        /* noop */
      }
    };
  }, [planId, load]);

  const approve = async (stepId: string) => {
    setBusyStep(stepId);
    try {
      await api.approvePlanStep(planId, stepId);
      await load();
    } finally {
      setBusyStep(null);
    }
  };

  // No per-step reject endpoint exists; rejecting a required approval cancels
  // the plan (the safest available action).
  const reject = async () => {
    setBusyStep("reject");
    try {
      await api.cancelPlan(planId);
      await load();
    } finally {
      setBusyStep(null);
    }
  };

  const retry = async (stepId: string) => {
    setBusyStep(stepId);
    try {
      await api.retryPlanStep(planId, stepId);
      await load();
    } finally {
      setBusyStep(null);
    }
  };

  const cancel = async () => {
    await api.cancelPlan(planId);
    await load();
  };

  const steps = plan?.steps ?? [];
  const screencaps = steps.filter((s) => s.screencap_path);
  const active = plan && ["pending", "running"].includes(plan.status);

  return (
    <div className="animate-fade-up">
      <div className="mb-5 flex items-start justify-between gap-4">
        <div className="flex items-start gap-3">
          <Button variant="ghost" size="icon" aria-label="Back" onClick={onBack}>
            <ArrowLeft size={18} />
          </Button>
          <div>
            <h2 className="text-lg font-medium text-ink">
              {plan?.goal ?? "Plan"}
            </h2>
            {plan && (
              <div className="mt-1 flex flex-wrap items-center gap-2 text-xs text-ink-faint">
                <StatusBadge label={plan.status} tone={planTone(plan.status)} />
                <span>trust: {plan.trust_level}</span>
                {plan.parallel && <span>· parallel</span>}
              </div>
            )}
          </div>
        </div>
        {active && (
          <Button variant="danger" size="sm" onClick={() => void cancel()}>
            <X size={14} /> Cancel plan
          </Button>
        )}
      </div>

      {offline && (
        <p className="mb-4 text-xs text-ink-faint">
          Backend unreachable — connect the server to view this plan.
        </p>
      )}

      {plan?.error && (
        <GlassPanel soft className="mb-5 p-4">
          <p className="text-sm text-danger">{plan.error}</p>
        </GlassPanel>
      )}

      {/* Step timeline */}
      <section className="mb-6">
        <h3 className="eyebrow mb-3">Steps</h3>
        {steps.length === 0 ? (
          <p className="text-sm text-ink-faint">No steps in this plan.</p>
        ) : (
          <ol className="space-y-2">
            {steps.map((s) => (
              <li key={s.id}>
                <GlassPanel soft className="p-4">
                  <div className="flex items-start justify-between gap-3">
                    <div className="min-w-0">
                      <div className="flex items-center gap-2">
                        <span className="text-xs text-ink-faint">
                          #{s.step_order}
                        </span>
                        <span className="text-sm font-medium text-ink">
                          {s.action}
                        </span>
                      </div>
                      {s.args_json && (
                        <p className="mt-1 break-words font-mono text-[0.7rem] text-ink-faint">
                          {s.args_json}
                        </p>
                      )}
                      {s.result && (
                        <p className="mt-1 break-words text-xs text-ink-soft">
                          {s.result}
                        </p>
                      )}
                      {s.error && (
                        <p className="mt-1 break-words text-xs text-danger">
                          {s.error}
                        </p>
                      )}
                    </div>
                    <div className="flex shrink-0 flex-col items-end gap-2">
                      <StatusBadge label={s.status} tone={stepTone(s.status)} />
                      <div className="flex gap-1.5">
                        {s.status === "pending_approval" && (
                          <>
                            <Button
                              variant="primary"
                              size="sm"
                              disabled={busyStep === s.id}
                              onClick={() => void approve(s.id)}
                            >
                              <Check size={13} /> Approve
                            </Button>
                            <Button
                              variant="danger"
                              size="sm"
                              disabled={busyStep !== null}
                              onClick={() => void reject()}
                            >
                              <X size={13} /> Reject
                            </Button>
                          </>
                        )}
                        {(s.status === "failed" || s.status === "rejected") && (
                          <Button
                            variant="subtle"
                            size="sm"
                            disabled={busyStep === s.id}
                            onClick={() => void retry(s.id)}
                          >
                            <RotateCcw size={13} /> Retry
                            {s.retries > 0 ? ` (${s.retries})` : ""}
                          </Button>
                        )}
                      </div>
                    </div>
                  </div>
                </GlassPanel>
              </li>
            ))}
          </ol>
        )}
      </section>

      {/* Sub-plans */}
      {subPlans.length > 0 && (
        <section className="mb-6">
          <h3 className="eyebrow mb-3 flex items-center gap-2">
            <GitBranch size={13} className="text-accent" /> Sub-plans
          </h3>
          <ul className="space-y-2">
            {subPlans.map((sp) => (
              <li key={sp.id}>
                <GlassPanel
                  soft
                  className="flex items-center justify-between p-3"
                >
                  <span className="min-w-0 truncate text-sm text-ink">
                    {sp.goal}
                  </span>
                  <StatusBadge label={sp.status} tone={planTone(sp.status)} />
                </GlassPanel>
              </li>
            ))}
          </ul>
        </section>
      )}

      {/* Screencap gallery */}
      {screencaps.length > 0 && (
        <section className="mb-6">
          <h3 className="eyebrow mb-3 flex items-center gap-2">
            <ImageIcon size={13} className="text-accent" /> Screencaptures
          </h3>
          <div className="grid grid-cols-2 gap-3 sm:grid-cols-3">
            {screencaps.map((s) => {
              const src = (s.screencap_path ?? "").startsWith("http")
                ? (s.screencap_path as string)
                : `${apiOrigin}/${(s.screencap_path ?? "").replace(/^\/+/, "")}`;
              return (
                <figure
                  key={s.id}
                  className="glass-soft overflow-hidden rounded"
                >
                  <img
                    src={src}
                    alt={`step ${s.step_order} capture`}
                    className="h-28 w-full object-cover"
                    loading="lazy"
                    onError={(e) => {
                      (e.currentTarget as HTMLImageElement).style.display =
                        "none";
                    }}
                  />
                  <figcaption className="truncate px-2 py-1 text-[0.65rem] text-ink-faint">
                    #{s.step_order} · {s.action}
                  </figcaption>
                </figure>
              );
            })}
          </div>
        </section>
      )}

      {/* Live logs */}
      <section>
        <h3 className="eyebrow mb-3">Live events</h3>
        <GlassPanel soft className="p-3">
          {logs.length === 0 ? (
            <p className="text-xs text-ink-faint">
              Listening for real-time updates…
            </p>
          ) : (
            <ScrollArea className="max-h-40">
              <ul className="space-y-1">
                {logs.map((l, i) => (
                  <li
                    key={i}
                    className={cn(
                      "font-mono text-[0.7rem]",
                      i === 0 ? "text-ink-soft" : "text-ink-faint",
                    )}
                  >
                    {l}
                  </li>
                ))}
              </ul>
            </ScrollArea>
          )}
        </GlassPanel>
      </section>
    </div>
  );
}

import { useCallback, useEffect, useRef, useState } from "react";
import { ChevronRight, RefreshCw, GitBranch } from "lucide-react";
import { PageContainer } from "@/components/layout/PageContainer";
import { ScrollArea } from "@/components/ui/ScrollArea";
import { GlassPanel } from "@/components/ui/GlassPanel";
import { Button } from "@/components/ui/Button";
import { StatusBadge } from "@/components/ui/StatusBadge";
import { api } from "@/lib/api";
import type { ApiPlan } from "@/lib/types";
import { PlanDetail } from "./PlanDetail";
import { planTone, statusWsUrl } from "./planStatus";

function formatWhen(iso: string): string {
  const t = Date.parse(iso);
  if (!t) return "";
  return new Date(t).toLocaleString();
}

export function PlansView() {
  const [plans, setPlans] = useState<ApiPlan[]>([]);
  const [offline, setOffline] = useState(false);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const wsRef = useRef<WebSocket | null>(null);
  const closedRef = useRef(false);

  const load = useCallback(async () => {
    const r = await api.listPlans();
    setOffline(!r.ok);
    if (r.ok) setPlans(r.data);
    else setPlans([]);
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  // Refresh the list whenever a plan-level event fires on /ws/status.
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
          if (type.startsWith("plan") || type.startsWith("subplan")) void load();
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
  }, [load]);

  if (selectedId) {
    return (
      <ScrollArea className="h-full">
        <div className="mx-auto max-w-4xl px-8 py-8">
          <PlanDetail
            planId={selectedId}
            onBack={() => {
              setSelectedId(null);
              void load();
            }}
          />
        </div>
      </ScrollArea>
    );
  }

  return (
    <PageContainer
      title="Plans"
      subtitle="Computer-control execution plans Miori runs on your behalf."
      actions={
        <Button variant="subtle" size="sm" onClick={() => void load()}>
          <RefreshCw size={14} /> Refresh
        </Button>
      }
    >
      {offline && (
        <p className="mb-4 text-xs text-ink-faint">
          Backend unreachable — connect the server to view plans.
        </p>
      )}

      {plans.length === 0 ? (
        <GlassPanel soft className="rounded-lg px-6 py-16 text-center">
          <p className="text-sm text-ink-soft">No plans yet</p>
          <p className="mt-1 text-xs text-ink-faint">
            Plans appear here when Miori decomposes a computer-control task.
          </p>
        </GlassPanel>
      ) : (
        <ul className="space-y-2">
          {plans.map((p) => (
            <li key={p.id}>
              <button
                onClick={() => setSelectedId(p.id)}
                className="group w-full text-left"
              >
                <GlassPanel
                  soft
                  className="flex items-center gap-3 p-4 transition-colors group-hover:bg-white/[0.06]"
                >
                  <div className="min-w-0 flex-1">
                    <div className="flex items-center gap-2">
                      <span className="truncate text-sm font-medium text-ink">
                        {p.goal}
                      </span>
                      {p.parallel && (
                        <span className="inline-flex items-center gap-1 text-[0.65rem] text-ink-faint">
                          <GitBranch size={11} /> parallel
                        </span>
                      )}
                    </div>
                    <div className="mt-1 flex flex-wrap items-center gap-2 text-xs text-ink-faint">
                      <span>trust: {p.trust_level}</span>
                      <span>· {formatWhen(p.created_at)}</span>
                    </div>
                  </div>
                  <StatusBadge label={p.status} tone={planTone(p.status)} />
                  <ChevronRight
                    size={16}
                    className="text-ink-faint transition-colors group-hover:text-ink-soft"
                  />
                </GlassPanel>
              </button>
            </li>
          ))}
        </ul>
      )}
    </PageContainer>
  );
}

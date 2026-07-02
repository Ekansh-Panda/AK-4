import { useCallback, useEffect, useRef, useState } from "react";
import {
  Cpu,
  MemoryStick,
  Clock,
  MonitorSmartphone,
  RefreshCw,
  ListTodo,
  Smartphone,
  CircleSlash,
} from "lucide-react";
import { cn } from "@/lib/cn";
import { GlassCard } from "@/components/GlassCard";
import { ScreenHeader } from "@/components/ScreenHeader";
import { StatusDot } from "@/components/StatusDot";
import { Button } from "@/components/Button";
import { getDeviceStatus, getTasks } from "@/lib/api";
import { useConnection } from "@/state/connection";
import type { DeviceStatus, TaskItem } from "@/lib/types";

/**
 * Host vitals — online state, device/task counts, and the task list. Pulls live
 * data from the backend (synthesised from /health + /remote/devices + /tasks),
 * with a clear "remote disabled" state when the host runs without
 * REMOTE_ENABLED, and an offline mock fallback when unreachable.
 */
export function DeviceScreen() {
  const { host, token } = useConnection();
  const [status, setStatus] = useState<DeviceStatus | null>(null);
  const [tasks, setTasks] = useState<TaskItem[]>([]);
  const [loading, setLoading] = useState(false);
  const timerRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const refresh = useCallback(async () => {
    setLoading(true);
    try {
      const [next, taskList] = await Promise.all([
        getDeviceStatus({ host, token }),
        getTasks({ host, token }),
      ]);
      setStatus(next);
      setTasks(taskList);
    } finally {
      setLoading(false);
    }
  }, [host, token]);

  // Poll every 4s for fresh vitals.
  useEffect(() => {
    void refresh();
    timerRef.current = setInterval(refresh, 4000);
    return () => {
      if (timerRef.current) clearInterval(timerRef.current);
    };
  }, [refresh]);

  const source = status?.source;
  const disabled = source === "disabled";
  const mock = source === "mock";
  // Live but unmetered hosts report 0/0/0 — hide the synthetic gauges then.
  const showGauges = mock || (status != null && status.memTotalGb > 0);

  return (
    <main className="flex min-h-dvh flex-col">
      <ScreenHeader title="Device" subtitle="How the host is feeling" />

      <div className="mx-auto w-full max-w-md flex-1 px-5 pb-28">
        {/* Online / power summary */}
        <GlassCard elevated className="mb-3 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <StatusDot
              tone={status?.online ? "positive" : "idle"}
              pulse={status?.online}
            />
            <div>
              <p className="font-medium">
                {status?.online ? "Online" : "Offline"}
              </p>
              <p className="text-xs text-ink-faint">
                {!status
                  ? "Reading vitals…"
                  : disabled
                    ? "Host up · remote control off"
                    : status.power === "awake"
                      ? "Awake and responsive"
                      : "Sleeping — idling low"}
              </p>
            </div>
          </div>
          <Button
            variant="ghost"
            onClick={refresh}
            loading={loading}
            aria-label="Refresh"
            className="h-10 w-10 px-0"
          >
            {!loading && <RefreshCw className="h-4 w-4" aria-hidden />}
          </Button>
        </GlassCard>

        {/* Counts */}
        <div className="mb-3 grid grid-cols-2 gap-3">
          <Fact
            icon={<Smartphone className="h-4 w-4" aria-hidden />}
            label="Devices"
            value={status ? String(status.deviceCount) : "—"}
          />
          <Fact
            icon={<ListTodo className="h-4 w-4" aria-hidden />}
            label="Tasks"
            value={status ? String(status.taskCount) : "—"}
          />
        </div>

        {/* Remote-disabled notice */}
        {disabled && (
          <GlassCard className="mb-3 flex items-start gap-3">
            <CircleSlash className="mt-0.5 h-4 w-4 shrink-0 text-warn" aria-hidden />
            <p className="text-xs leading-relaxed text-ink-soft">
              Remote device control is <span className="text-ink">disabled</span> on
              this host. Start the backend with{" "}
              <code className="font-mono text-ink">REMOTE_ENABLED=true</code> to wake,
              sleep, and pair devices. Chat, files, and tasks still work.
            </p>
          </GlassCard>
        )}

        {/* Gauges (mock-only synthetic metrics; live hosts are unmetered for now) */}
        {showGauges && (
          <div className="grid grid-cols-1 gap-3">
            <Gauge
              icon={<Cpu className="h-4 w-4" aria-hidden />}
              label="CPU load"
              value={status?.cpu ?? 0}
              unit="%"
            />
            <Gauge
              icon={<MemoryStick className="h-4 w-4" aria-hidden />}
              label="Memory"
              value={status?.mem ?? 0}
              unit="%"
              note={
                status && status.memTotalGb > 0
                  ? `${gb(status)} of ${status.memTotalGb} GB`
                  : undefined
              }
            />
          </div>
        )}

        {/* Facts */}
        <div className="mt-3 grid grid-cols-2 gap-3">
          <Fact
            icon={<Clock className="h-4 w-4" aria-hidden />}
            label="Uptime"
            value={
              status && status.uptimeSec > 0
                ? formatUptime(status.uptimeSec)
                : mock
                  ? formatUptime(status?.uptimeSec ?? 0)
                  : "—"
            }
          />
          <Fact
            icon={<MonitorSmartphone className="h-4 w-4" aria-hidden />}
            label="Platform"
            value={status?.platform ?? "—"}
          />
        </div>

        {/* Tasks */}
        <section className="mt-5">
          <h2 className="mb-2 flex items-center gap-2 px-1 text-sm font-semibold text-ink-soft">
            <ListTodo className="h-4 w-4" aria-hidden />
            Tasks
          </h2>
          {tasks.length === 0 ? (
            <GlassCard className="text-center text-sm text-ink-faint">
              No tasks on the host yet.
            </GlassCard>
          ) : (
            <div className="flex flex-col gap-2">
              {tasks.map((t) => (
                <TaskRow key={t.id} task={t} />
              ))}
            </div>
          )}
        </section>

        {mock && (
          <p className="mt-5 rounded-xl border border-warn/25 bg-warn/[0.06] px-4 py-2.5 text-center text-xs text-warn">
            Offline — showing simulated vitals. These become live once the host
            at the configured address is reachable.
          </p>
        )}
      </div>
    </main>
  );
}

function gb(s: DeviceStatus): string {
  return ((s.mem / 100) * s.memTotalGb).toFixed(1);
}

const STATUS_TONE: Record<string, "positive" | "warn" | "idle" | "danger"> = {
  done: "positive",
  completed: "positive",
  in_progress: "warn",
  running: "warn",
  pending: "idle",
  failed: "danger",
  error: "danger",
};

function TaskRow({ task }: { task: TaskItem }) {
  const tone = STATUS_TONE[task.status] ?? "idle";
  return (
    <GlassCard className="flex items-center gap-3 py-3">
      <StatusDot tone={tone} pulse={tone === "warn"} />
      <div className="min-w-0 flex-1">
        <p className="truncate text-sm font-medium">{task.title}</p>
        {task.description && (
          <p className="truncate text-xs text-ink-faint">{task.description}</p>
        )}
      </div>
      <span className="shrink-0 rounded-full bg-white/[0.05] px-2.5 py-1 text-[10px] font-medium uppercase tracking-wide text-ink-soft">
        {task.status.replace(/_/g, " ")}
      </span>
    </GlassCard>
  );
}

function Gauge({
  icon,
  label,
  value,
  unit,
  note,
}: {
  icon: React.ReactNode;
  label: string;
  value: number;
  unit: string;
  note?: string;
}) {
  const tone =
    value >= 85 ? "bg-danger" : value >= 60 ? "bg-warn" : "bg-accent";
  return (
    <GlassCard>
      <div className="mb-2 flex items-center justify-between">
        <span className="flex items-center gap-2 text-sm text-ink-soft">
          {icon}
          {label}
        </span>
        <span className="font-mono text-lg font-medium tabular-nums">
          {Math.round(value)}
          <span className="text-sm text-ink-faint">{unit}</span>
        </span>
      </div>
      <div className="h-2 overflow-hidden rounded-full bg-white/[0.06]">
        <div
          className={cn("h-full rounded-full transition-[width] duration-700 ease-soft", tone)}
          style={{ width: `${Math.max(2, Math.min(100, value))}%` }}
        />
      </div>
      {note && <p className="mt-1.5 text-xs text-ink-faint">{note}</p>}
    </GlassCard>
  );
}

function Fact({
  icon,
  label,
  value,
}: {
  icon: React.ReactNode;
  label: string;
  value: string;
}) {
  return (
    <GlassCard>
      <span className="flex items-center gap-2 text-xs text-ink-faint">
        {icon}
        {label}
      </span>
      <p className="mt-1 text-base font-medium">{value}</p>
    </GlassCard>
  );
}

function formatUptime(sec: number): string {
  const h = Math.floor(sec / 3600);
  const m = Math.floor((sec % 3600) / 60);
  if (h > 0) return `${h}h ${m}m`;
  return `${m}m`;
}

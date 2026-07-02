import { useEffect, useState } from "react";
import { Laptop, Smartphone, Monitor, Wifi, WifiOff } from "lucide-react";
import { PageContainer } from "@/components/layout/PageContainer";
import { Button } from "@/components/ui/Button";
import { useConnection } from "@/state/ConnectionStore";
import { connectionTone } from "@/components/ui/StatusBadge";
import { api } from "@/lib/api";
import { cn } from "@/lib/cn";
import type { ApiDevice } from "@/lib/types";

function platformIcon(platform: string | null) {
  const p = (platform ?? "").toLowerCase();
  if (p.includes("mac") || p.includes("darwin")) return Laptop;
  if (p.includes("phone") || p.includes("ios") || p.includes("android") || p.includes("web"))
    return Smartphone;
  return Monitor;
}

function relativeTime(iso: string | null): string {
  if (!iso) return "never";
  const ts = Date.parse(iso);
  if (Number.isNaN(ts)) return "unknown";
  const diff = Date.now() - ts;
  const min = Math.round(diff / 60000);
  if (min < 1) return "just now";
  if (min < 60) return `${min}m ago`;
  return `${Math.round(min / 60)}h ago`;
}

function DeviceCard({ d }: { d: ApiDevice }) {
  const Icon = platformIcon(d.platform);
  const online = d.state === "online";
  return (
    <article className="glass-soft flex items-center gap-4 rounded-lg p-4">
      <div className="grid h-10 w-10 place-items-center rounded bg-white/[0.05]">
        <Icon size={20} className="text-ink-soft" />
      </div>
      <div className="min-w-0 flex-1">
        <div className="flex items-center gap-2">
          <span className="text-sm font-medium text-ink">{d.name}</span>
          {online ? (
            <Wifi size={13} className="text-positive" />
          ) : (
            <WifiOff size={13} className="text-ink-faint" />
          )}
        </div>
        <div className="mt-0.5 text-xs text-ink-faint">
          {d.platform ?? "unknown"} · {d.state}
          {!online && ` · seen ${relativeTime(d.last_seen_at)}`}
          {d.is_paired ? " · paired" : " · unpaired"}
        </div>
      </div>
      <Button variant="subtle" size="sm" disabled>
        {online ? "Online" : "Offline"}
      </Button>
    </article>
  );
}

export function RemoteView() {
  const { status, health, refresh } = useConnection();
  const conn = connectionTone(status);
  const remoteEnabled = health?.remote_enabled ?? false;

  const [devices, setDevices] = useState<ApiDevice[]>([]);
  const [loaded, setLoaded] = useState(false);

  useEffect(() => {
    if (!remoteEnabled) {
      setDevices([]);
      setLoaded(true);
      return;
    }
    let cancelled = false;
    void api.listDevices().then((r) => {
      if (cancelled) return;
      setDevices(r.data);
      setLoaded(true);
    });
    return () => {
      cancelled = true;
    };
  }, [remoteEnabled, status]);

  return (
    <PageContainer
      title="Remote"
      subtitle="Reach Miori from any of your devices."
      actions={
        <Button variant="subtle" size="sm" onClick={refresh}>
          Refresh
        </Button>
      }
    >
      <div className="glass-soft mb-6 flex items-center justify-between rounded-lg px-4 py-3">
        <span className="text-sm text-ink-soft">Backend link</span>
        <span className="inline-flex items-center gap-2 text-sm text-ink">
          <span
            className={cn(
              "h-2 w-2 rounded-full",
              conn.tone === "positive"
                ? "bg-positive"
                : conn.tone === "warn"
                  ? "bg-warn"
                  : "bg-ink-faint",
            )}
          />
          {conn.label}
        </span>
      </div>

      {!remoteEnabled ? (
        <div className="glass-soft rounded-lg px-5 py-8 text-center">
          <p className="text-sm text-ink">Remote access is disabled.</p>
          <p className="mt-1 text-xs text-ink-faint">
            {status === "connected"
              ? "The backend has REMOTE_ENABLED off. Enable it server-side to pair devices."
              : "Connect to a backend to manage remote devices."}
          </p>
        </div>
      ) : (
        <div className="space-y-3">
          {devices.map((d) => (
            <DeviceCard key={d.id} d={d} />
          ))}
          {loaded && devices.length === 0 && (
            <p className="text-sm text-ink-faint">No devices registered yet.</p>
          )}
        </div>
      )}
    </PageContainer>
  );
}

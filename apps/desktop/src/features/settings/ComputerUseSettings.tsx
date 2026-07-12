import { useEffect, useState, type ReactNode } from "react";
import { Save } from "lucide-react";
import { PageContainer } from "@/components/layout/PageContainer";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { api } from "@/lib/api";
import { cn } from "@/lib/cn";
import type { ApiComputerUseSettings } from "@/lib/types";

/** Available trust levels, least → most permissive. */
const TRUST_LEVELS = ["manual", "auto-shell", "trusted", "god"] as const;

const DEFAULTS: ApiComputerUseSettings = {
  trust_level: "manual",
  max_steps: 25,
  plan_timeout_s: 300,
  vision_enabled: false,
  audio_enabled: false,
  double_verify: true,
  browser_enabled: false,
};

function SettingRow({
  title,
  description,
  children,
}: {
  title: string;
  description: string;
  children: ReactNode;
}) {
  return (
    <section className="glass-soft rounded-lg p-5">
      <div className="mb-4">
        <h3 className="text-sm font-medium text-ink">{title}</h3>
        <p className="mt-0.5 text-xs text-ink-faint">{description}</p>
      </div>
      {children}
    </section>
  );
}

function Toggle({
  label,
  value,
  onChange,
}: {
  label: string;
  value: boolean;
  onChange: (v: boolean) => void;
}) {
  return (
    <button
      type="button"
      onClick={() => onChange(!value)}
      className={cn(
        "flex w-full items-center justify-between rounded px-4 py-3 text-left transition-colors",
        value ? "border border-accent/40 bg-accent/10" : "border border-white/[0.06]",
      )}
    >
      <span className="text-sm text-ink">{label}</span>
      <span
        className={cn(
          "relative h-5 w-9 rounded-full transition-colors",
          value ? "bg-accent" : "bg-white/15",
        )}
      >
        <span
          className={cn(
            "absolute top-0.5 h-4 w-4 rounded-full bg-canvas transition-all",
            value ? "left-[1.125rem]" : "left-0.5",
          )}
        />
      </span>
    </button>
  );
}

export function ComputerUseSettings() {
  const [form, setForm] = useState<ApiComputerUseSettings>(DEFAULTS);
  const [offline, setOffline] = useState(false);
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);
  const [auditLog, setAuditLog] = useState<any[]>([]);

  const patch = <K extends keyof ApiComputerUseSettings>(
    key: K,
    value: ApiComputerUseSettings[K],
  ) => {
    setForm((prev) => ({ ...prev, [key]: value }));
    setSaved(false);
  };

  useEffect(() => {
    void api.getComputerUseSettings().then((r) => {
      setOffline(!r.ok);
      if (r.ok && r.data) setForm(r.data);
    });
    void api.getComputerUseAudit().then((r) => {
      if (r.ok && r.data) setAuditLog(r.data);
    });
  }, []);

  const save = async () => {
    setSaving(true);
    try {
      const r = await api.updateComputerUseSettings(form);
      if (r.ok) {
        if (r.data) setForm(r.data);
        setSaved(true);
      }
    } finally {
      setSaving(false);
    }
  };

  return (
    <PageContainer
      title="Computer Use"
      subtitle="Control how much autonomy Miori has over your machine."
      actions={
        <Button variant="primary" size="sm" disabled={saving} onClick={() => void save()}>
          <Save size={14} /> {saved ? "Saved" : "Save"}
        </Button>
      }
    >
      <div className="space-y-5">
        {offline && (
          <p className="text-xs text-ink-faint">
            Backend unreachable — showing defaults (changes won't persist).
          </p>
        )}

        {/* Trust level */}
        <SettingRow
          title="Trust level"
          description="How much Miori can do without asking. 'god' skips all approvals — use with care."
        >
          <div className="grid gap-2 sm:grid-cols-2">
            {TRUST_LEVELS.map((level) => (
              <button
                key={level}
                onClick={() => patch("trust_level", level)}
                className={cn(
                  "flex items-center justify-between rounded px-4 py-2.5 text-left capitalize transition-colors",
                  form.trust_level === level
                    ? "border border-accent/40 bg-accent/10"
                    : "border border-white/[0.06] hover:bg-white/[0.04]",
                )}
              >
                <span className="text-sm text-ink">{level}</span>
                {level === "god" && (
                  <span className="text-[0.65rem] text-negative">high risk</span>
                )}
              </button>
            ))}
          </div>
        </SettingRow>

        {/* Capabilities */}
        <SettingRow
          title="Capabilities"
          description="Enable the sensory + safety features Miori may use while executing plans."
        >
          <div className="space-y-2">
            <Toggle
              label="Vision (screen understanding)"
              value={form.vision_enabled}
              onChange={(v) => patch("vision_enabled", v)}
            />
            <Toggle
              label="Audio (listen / speak)"
              value={form.audio_enabled}
              onChange={(v) => patch("audio_enabled", v)}
            />
            <Toggle
              label="Double-verify destructive actions"
              value={form.double_verify}
              onChange={(v) => patch("double_verify", v)}
            />
            <Toggle
              label="Browser control"
              value={form.browser_enabled}
              onChange={(v) => patch("browser_enabled", v)}
            />
          </div>
        </SettingRow>

        {/* Limits */}
        <SettingRow
          title="Execution limits"
          description="Guardrails that bound how far a single plan can go."
        >
          <div className="grid gap-4 sm:grid-cols-2">
            <label className="block">
              <span className="mb-1.5 block text-xs text-ink-faint">Max steps</span>
              <Input
                type="number"
                min={1}
                value={String(form.max_steps)}
                onChange={(e) =>
                  patch("max_steps", Number(e.target.value) || 0)
                }
              />
            </label>
            <label className="block">
              <span className="mb-1.5 block text-xs text-ink-faint">
                Plan timeout (seconds)
              </span>
              <Input
                type="number"
                min={1}
                value={String(form.plan_timeout_s)}
                onChange={(e) =>
                  patch("plan_timeout_s", Number(e.target.value) || 0)
                }
              />
            </label>
          </div>
        </SettingRow>

        {/* Audit log */}
        <SettingRow
          title="Audit log"
          description="The most recent computer-use actions Miori has taken."
        >
          <div className="max-h-64 overflow-y-auto rounded border border-white/[0.06] bg-canvas-subtle p-4">
            {auditLog.length === 0 ? (
              <p className="text-xs italic text-ink-faint">No actions logged yet.</p>
            ) : (
              <ul className="space-y-3">
                {auditLog.map((log, i) => (
                  <li
                    key={i}
                    className="border-b border-white/[0.04] pb-2 text-xs last:border-0 last:pb-0"
                  >
                    <div className="mb-1 flex justify-between text-ink-faint">
                      <span>{new Date(log.ts).toLocaleString()}</span>
                      <span className="font-mono">{log.action}</span>
                    </div>
                    <div className="break-words text-ink">
                      <span className="opacity-60">Args:</span>{" "}
                      {JSON.stringify(log.args)}
                    </div>
                    <div
                      className={cn(
                        "mt-1",
                        log.error ? "text-negative" : "text-positive",
                      )}
                    >
                      {log.error ? `Error: ${log.error}` : `Outcome: ${log.outcome}`}
                    </div>
                  </li>
                ))}
              </ul>
            )}
          </div>
        </SettingRow>
      </div>
    </PageContainer>
  );
}

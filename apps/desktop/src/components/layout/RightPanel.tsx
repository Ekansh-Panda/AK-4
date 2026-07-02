import { type ReactNode } from "react";
import { Cpu, Wrench, Sparkles, MonitorSmartphone, Heart } from "lucide-react";
import { ScrollArea } from "@/components/ui/ScrollArea";
import { StatusBadge } from "@/components/ui/StatusBadge";
import { useConnection } from "@/state/ConnectionStore";
import { usePersona } from "@/state/PersonaStore";
import { cn } from "@/lib/cn";

function Section({
  icon: Icon,
  title,
  children,
}: {
  icon: typeof Cpu;
  title: string;
  children: ReactNode;
}) {
  return (
    <section className="px-4 py-4 border-b hairline last:border-0">
      <div className="mb-3 flex items-center gap-2">
        <Icon size={14} className="text-accent" />
        <span className="eyebrow">{title}</span>
      </div>
      {children}
    </section>
  );
}

export function RightPanel() {
  const { context } = useConnection();
  const { descriptor } = usePersona();
  const { model, tools, recentMemory, devices } = context;

  const activeTools = tools.filter((t) => t.active);

  return (
    <aside className="flex w-panel shrink-0 flex-col border-l hairline">
      <ScrollArea className="flex-1">
        {/* Current model */}
        <Section icon={Cpu} title="Model">
          <div className="text-sm text-ink">{model.label}</div>
          <div className="mt-0.5 text-xs text-ink-faint">
            {model.provider} · {(model.contextTokens / 1000).toFixed(0)}k ctx
            {model.local ? " · local" : ""}
          </div>
        </Section>

        {/* Active tools */}
        <Section icon={Wrench} title="Active tools">
          {activeTools.length === 0 ? (
            <p className="text-xs text-ink-faint">None active.</p>
          ) : (
            <div className="flex flex-wrap gap-1.5">
              {activeTools.map((t) => (
                <StatusBadge key={t.id} label={t.name} tone="positive" />
              ))}
            </div>
          )}
        </Section>

        {/* Recent memory hits */}
        <Section icon={Sparkles} title="Recent memory">
          <ul className="space-y-2.5">
            {recentMemory.map((hit) => (
              <li key={hit.id} className="text-xs">
                <p className="text-ink-soft leading-relaxed">{hit.snippet}</p>
                <p className="mt-0.5 text-ink-faint">
                  {hit.source} · {(hit.score * 100).toFixed(0)}%
                </p>
              </li>
            ))}
          </ul>
        </Section>

        {/* Devices */}
        <Section icon={MonitorSmartphone} title="Devices">
          <ul className="space-y-2">
            {devices.map((d) => (
              <li key={d.id} className="flex items-center justify-between text-xs">
                <span className="text-ink-soft">{d.name}</span>
                <span
                  className={cn(
                    "inline-flex items-center gap-1.5",
                    d.online ? "text-positive" : "text-ink-faint",
                  )}
                >
                  <span
                    className={cn(
                      "h-1.5 w-1.5 rounded-full",
                      d.online ? "bg-positive" : "bg-ink-faint",
                    )}
                  />
                  {d.online ? "online" : "offline"}
                </span>
              </li>
            ))}
          </ul>
        </Section>

        {/* Persona mode */}
        <Section icon={Heart} title="Persona">
          <div className="text-sm text-ink">{descriptor.label}</div>
          <p className="mt-0.5 text-xs text-ink-faint leading-relaxed">{descriptor.blurb}</p>
        </Section>
      </ScrollArea>
    </aside>
  );
}

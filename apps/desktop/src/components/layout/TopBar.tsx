import { useLocation } from "react-router-dom";
import { StatusBadge, connectionTone, presenceLabel } from "@/components/ui/StatusBadge";
import { useConnection } from "@/state/ConnectionStore";
import { usePersona } from "@/state/PersonaStore";
import { useChat } from "@/state/ChatStore";

const titles: Record<string, string> = {
  "/chat": "Chat",
  "/files": "Files",
  "/memory": "Memory",
  "/projects": "Projects",
  "/research": "Research",
  "/tasks": "Tasks",
  "/remote": "Remote",
  "/settings": "Settings",
};

export function TopBar() {
  const { pathname } = useLocation();
  const { status } = useConnection();
  const { descriptor } = usePersona();
  const { presence } = useChat();

  const conn = connectionTone(status);
  const title = titles[pathname] ?? "Miori";

  return (
    <header
      data-tauri-drag-region
      className="flex h-12 shrink-0 items-center justify-between border-b hairline px-5"
    >
      <div className="flex items-center gap-3">
        <h1 className="text-sm font-medium text-ink">{title}</h1>
        <span className="text-ink-faint">·</span>
        <span className="text-xs text-ink-faint">{presenceLabel(presence)}</span>
      </div>

      <div className="flex items-center gap-2">
        <StatusBadge label={descriptor.label} tone="accent" />
        <StatusBadge label={conn.label} tone={conn.tone} pulse={status === "connecting"} />
      </div>
    </header>
  );
}

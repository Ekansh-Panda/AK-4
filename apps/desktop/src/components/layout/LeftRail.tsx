import { NavLink } from "react-router-dom";
import {
  MessageCircle,
  FolderOpen,
  Brain,
  FolderKanban,
  Telescope,
  ListChecks,
  MonitorSmartphone,
  Settings,
} from "lucide-react";
import { cn } from "@/lib/cn";
import { PresenceOrb } from "./PresenceOrb";
import { usePresence } from "@/state/PresenceStore";

const nav = [
  { to: "/chat", label: "Chat", Icon: MessageCircle },
  { to: "/files", label: "Files", Icon: FolderOpen },
  { to: "/memory", label: "Memory", Icon: Brain },
  { to: "/projects", label: "Projects", Icon: FolderKanban },
  { to: "/research", label: "Research", Icon: Telescope },
  { to: "/tasks", label: "Tasks", Icon: ListChecks },
  { to: "/remote", label: "Remote", Icon: MonitorSmartphone },
  { to: "/settings", label: "Settings", Icon: Settings },
];

export function LeftRail() {
  const { presence } = usePresence();

  return (
    <nav className="flex w-railwide shrink-0 flex-col gap-1 p-3">
      {/* Identity / presence */}
      <div className="mb-4 flex items-center gap-3 px-2 pt-1">
        <PresenceOrb state={presence} size={34} />
        <div className="leading-tight">
          <div className="text-sm font-medium text-ink">Miori</div>
          <div className="text-[0.7rem] text-ink-faint">your companion</div>
        </div>
      </div>

      {nav.map(({ to, label, Icon }) => (
        <NavLink
          key={to}
          to={to}
          className={({ isActive }) =>
            cn(
              "group flex items-center gap-3 rounded px-3 py-2 text-sm transition-colors duration-200 ease-soft",
              isActive
                ? "glass-soft text-ink"
                : "text-ink-soft hover:text-ink hover:bg-white/[0.04]",
            )
          }
        >
          {({ isActive }) => (
            <>
              <Icon
                size={18}
                className={cn(
                  "shrink-0 transition-colors",
                  isActive ? "text-accent" : "text-ink-faint group-hover:text-ink-soft",
                )}
              />
              <span>{label}</span>
            </>
          )}
        </NavLink>
      ))}

      <div className="mt-auto px-3 pb-1 text-[0.65rem] text-ink-faint">
        Miori Core v1.1.0
      </div>
    </nav>
  );
}

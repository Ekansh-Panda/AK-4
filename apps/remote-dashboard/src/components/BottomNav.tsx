import { NavLink } from "react-router-dom";
import {
  MessageCircle,
  Activity,
  Power,
  Upload,
  Settings,
  type LucideIcon,
} from "lucide-react";
import { cn } from "@/lib/cn";

interface Tab {
  to: string;
  label: string;
  icon: LucideIcon;
}

const TABS: Tab[] = [
  { to: "/chat", label: "Chat", icon: MessageCircle },
  { to: "/device", label: "Device", icon: Activity },
  { to: "/power", label: "Power", icon: Power },
  { to: "/files", label: "Files", icon: Upload },
  { to: "/settings", label: "Settings", icon: Settings },
];

/**
 * Persistent bottom tab bar. Glassy, safe-area aware, big tap targets. Fixed to
 * the bottom of the viewport on every authed screen.
 */
export function BottomNav() {
  return (
    <nav
      className="fixed inset-x-0 bottom-0 z-30 pb-safe pl-safe pr-safe"
      aria-label="Primary"
    >
      <div className="mx-auto max-w-md px-3 pb-2">
        <div className="glass-elevated flex items-stretch justify-around rounded-2xl px-1 py-1.5">
          {TABS.map(({ to, label, icon: Icon }) => (
            <NavLink
              key={to}
              to={to}
              className={({ isActive }) =>
                cn(
                  "group relative flex flex-1 flex-col items-center justify-center gap-1 rounded-xl px-1 py-2",
                  "min-h-[52px] transition-colors duration-200 ease-soft",
                  isActive ? "text-accent-soft" : "text-ink-faint hover:text-ink-soft",
                )
              }
            >
              {({ isActive }) => (
                <>
                  {isActive && (
                    <span className="absolute inset-0 rounded-xl bg-accent/10" />
                  )}
                  <Icon
                    className={cn(
                      "relative h-5 w-5 transition-transform duration-200",
                      isActive && "scale-110",
                    )}
                    aria-hidden
                  />
                  <span className="relative text-[10px] font-medium tracking-wide">
                    {label}
                  </span>
                </>
              )}
            </NavLink>
          ))}
        </div>
      </div>
    </nav>
  );
}

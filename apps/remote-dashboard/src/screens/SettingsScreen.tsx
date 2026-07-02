import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { Server, KeyRound, Moon, Sun, LogOut, Check } from "lucide-react";
import { cn } from "@/lib/cn";
import { Button } from "@/components/Button";
import { GlassCard } from "@/components/GlassCard";
import { ScreenHeader } from "@/components/ScreenHeader";
import { StatusDot } from "@/components/StatusDot";
import { useConnection } from "@/state/connection";

/** Minimal settings: host, token, theme + disconnect. */
export function SettingsScreen() {
  const navigate = useNavigate();
  const {
    host,
    token,
    theme,
    setHost,
    setToken,
    setTheme,
    connect,
    disconnect,
    version,
    status,
    isConnected,
    isMock,
    remoteEnabled,
  } = useConnection();

  const [localHost, setLocalHost] = useState(host);
  const [localToken, setLocalToken] = useState(token);
  const [saved, setSaved] = useState(false);

  async function saveAndReconnect() {
    setHost(localHost);
    setToken(localToken);
    setSaved(true);
    setTimeout(() => setSaved(false), 1600);
    await connect({ host: localHost, token: localToken });
  }

  function onDisconnect() {
    disconnect();
    navigate("/login", { replace: true });
  }

  return (
    <main className="flex min-h-dvh flex-col">
      <ScreenHeader title="Settings" subtitle="Connection & appearance" />

      <div className="mx-auto w-full max-w-md flex-1 px-5 pb-28">
        {/* Connection */}
        <GlassCard className="mb-3 flex flex-col gap-4">
          <h2 className="text-sm font-semibold text-ink-soft">Connection</h2>

          {/* Live connection state */}
          <div className="flex items-center gap-2.5 rounded-xl bg-white/[0.03] px-3 py-2.5">
            <StatusDot
              tone={
                !isConnected
                  ? "idle"
                  : isMock
                    ? "warn"
                    : status === "error"
                      ? "danger"
                      : "positive"
              }
              pulse={isConnected && !isMock}
            />
            <div className="min-w-0 flex-1">
              <p className="text-sm font-medium">
                {!isConnected
                  ? "Not connected"
                  : isMock
                    ? "Offline demo (mock)"
                    : "Live — connected to host"}
              </p>
              <p className="truncate text-xs text-ink-faint">
                {isConnected && !isMock
                  ? remoteEnabled
                    ? "Remote control enabled"
                    : "Remote control off (set REMOTE_ENABLED=true)"
                  : isMock
                    ? "Host unreachable — using simulated data"
                    : "Enter a host and connect"}
              </p>
            </div>
          </div>

          <label className="flex flex-col gap-1.5">
            <span className="flex items-center gap-1.5 text-xs text-ink-faint">
              <Server className="h-3.5 w-3.5" aria-hidden />
              Host address
            </span>
            <input
              className="field"
              type="url"
              inputMode="url"
              autoCapitalize="none"
              spellCheck={false}
              value={localHost}
              onChange={(e) => setLocalHost(e.target.value)}
            />
          </label>

          <label className="flex flex-col gap-1.5">
            <span className="flex items-center gap-1.5 text-xs text-ink-faint">
              <KeyRound className="h-3.5 w-3.5" aria-hidden />
              Pairing token
            </span>
            <input
              className="field"
              type="password"
              autoCapitalize="none"
              spellCheck={false}
              value={localToken}
              onChange={(e) => setLocalToken(e.target.value)}
            />
          </label>

          <Button full onClick={saveAndReconnect}>
            {saved ? (
              <>
                <Check className="h-4 w-4" aria-hidden /> Saved
              </>
            ) : (
              "Save & reconnect"
            )}
          </Button>
        </GlassCard>

        {/* Appearance */}
        <GlassCard className="mb-3 flex flex-col gap-3">
          <h2 className="text-sm font-semibold text-ink-soft">Appearance</h2>
          <div className="grid grid-cols-2 gap-2">
            <ThemeOption
              active={theme === "dark"}
              onClick={() => setTheme("dark")}
              icon={<Moon className="h-4 w-4" aria-hidden />}
              label="Midnight"
            />
            <ThemeOption
              active={theme === "dusk"}
              onClick={() => setTheme("dusk")}
              icon={<Sun className="h-4 w-4" aria-hidden />}
              label="Dusk"
            />
          </div>
          <p className="text-xs text-ink-faint">
            Both stay easy on the eyes — Miori never goes glaringly bright.
          </p>
        </GlassCard>

        {/* Session */}
        <GlassCard className="flex flex-col gap-3">
          <h2 className="text-sm font-semibold text-ink-soft">Session</h2>
          <Button variant="danger" full onClick={onDisconnect}>
            <LogOut className="h-4 w-4" aria-hidden />
            Disconnect
          </Button>
        </GlassCard>

        <p className="mt-5 text-center text-xs text-ink-faint">
          Miori Core · remote dashboard v0.1.0
          {version && ` · host ${version}`}
        </p>
      </div>
    </main>
  );
}

function ThemeOption({
  active,
  onClick,
  icon,
  label,
}: {
  active: boolean;
  onClick: () => void;
  icon: React.ReactNode;
  label: string;
}) {
  return (
    <button
      onClick={onClick}
      className={cn(
        "flex h-14 items-center justify-center gap-2 rounded-xl border text-sm transition-all",
        active
          ? "border-accent/50 bg-accent/15 text-accent-soft"
          : "border-white/[0.07] bg-white/[0.03] text-ink-soft hover:bg-white/[0.06]",
      )}
    >
      {icon}
      {label}
    </button>
  );
}

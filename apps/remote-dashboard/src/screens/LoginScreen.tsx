import { useState, type FormEvent } from "react";
import { useNavigate } from "react-router-dom";
import { KeyRound, Server, ShieldCheck } from "lucide-react";
import { Button } from "@/components/Button";
import { GlassCard } from "@/components/GlassCard";
import { PresenceOrb } from "@/components/PresenceOrb";
import { useConnection } from "@/state/connection";

/**
 * Login / pairing screen. Host address + token, "Connect". Auth is mocked
 * (see lib/api.ts → connect). On success we route into the chat tab.
 */
export function LoginScreen() {
  const navigate = useNavigate();
  const { host, token, setHost, setToken, connect, status, error } =
    useConnection();
  const [localHost, setLocalHost] = useState(host || "http://192.168.1.20:8000");
  const [localToken, setLocalToken] = useState(token);
  const connecting = status === "connecting";

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    setHost(localHost);
    setToken(localToken);
    const ok = await connect({ host: localHost, token: localToken });
    if (ok) navigate("/chat", { replace: true });
  }

  return (
    <main className="min-h-dvh flex flex-col px-5 pt-safe pb-safe">
      <div className="mx-auto flex w-full max-w-md flex-1 flex-col justify-center py-10">
        <header className="mb-8 flex flex-col items-center text-center">
          <PresenceOrb mood="awake" size="h-28 w-28" />
          <h1 className="mt-6 text-2xl font-semibold tracking-tight">
            Reach Miori
          </h1>
          <p className="mt-2 max-w-xs text-sm leading-relaxed text-ink-soft">
            Point your phone at the host machine and pair with its token. I'll be
            right there.
          </p>
        </header>

        <GlassCard className="p-5">
          <form onSubmit={onSubmit} className="flex flex-col gap-4">
            <label className="flex flex-col gap-1.5">
              <span className="flex items-center gap-1.5 text-xs font-medium text-ink-soft">
                <Server className="h-3.5 w-3.5" aria-hidden />
                Host address
              </span>
              <input
                className="field"
                type="url"
                inputMode="url"
                autoComplete="off"
                autoCapitalize="none"
                spellCheck={false}
                placeholder="http://192.168.1.20:8000"
                value={localHost}
                onChange={(e) => setLocalHost(e.target.value)}
              />
            </label>

            <label className="flex flex-col gap-1.5">
              <span className="flex items-center gap-1.5 text-xs font-medium text-ink-soft">
                <KeyRound className="h-3.5 w-3.5" aria-hidden />
                Pairing token
              </span>
              <input
                className="field"
                type="password"
                autoComplete="off"
                autoCapitalize="none"
                spellCheck={false}
                placeholder="paste the host's token"
                value={localToken}
                onChange={(e) => setLocalToken(e.target.value)}
              />
            </label>

            {error && (
              <p className="text-sm text-danger" role="alert">
                {error}
              </p>
            )}

            <Button type="submit" size="lg" full loading={connecting}>
              {connecting ? "Connecting" : "Connect"}
            </Button>
          </form>
        </GlassCard>

        <p className="mt-6 flex items-center justify-center gap-1.5 text-center text-xs text-ink-faint">
          <ShieldCheck className="h-3.5 w-3.5" aria-hidden />
          LAN-only · falls back to an offline demo if the host is unreachable
        </p>
      </div>
    </main>
  );
}

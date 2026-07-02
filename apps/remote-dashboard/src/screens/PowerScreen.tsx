import { useCallback, useEffect, useState } from "react";
import { Moon, Sun, CircleSlash } from "lucide-react";
import { cn } from "@/lib/cn";
import { Button } from "@/components/Button";
import { GlassCard } from "@/components/GlassCard";
import { PresenceOrb } from "@/components/PresenceOrb";
import { ScreenHeader } from "@/components/ScreenHeader";
import { getDeviceStatus, setPowerState } from "@/lib/api";
import { useConnection } from "@/state/connection";
import type { PowerState } from "@/lib/types";

/**
 * Wake / Sleep control for the host's primary device.
 *
 * Reads the current state from the device status (live or mock) and issues
 * POST /remote/devices/{id}/wake|sleep against it. When the host has remote
 * control disabled, the control is shown but clearly labelled as unavailable.
 */
export function PowerScreen() {
  const { host, token } = useConnection();
  const [power, setPower] = useState<PowerState>("awake");
  const [deviceId, setDeviceId] = useState<string | undefined>();
  const [disabled, setDisabled] = useState(false);
  const [busy, setBusy] = useState(false);

  // Hydrate current power/device from a status read.
  const hydrate = useCallback(async () => {
    const status = await getDeviceStatus({ host, token });
    setPower(status.power);
    setDeviceId(status.deviceId);
    setDisabled(status.source === "disabled");
  }, [host, token]);

  useEffect(() => {
    void hydrate();
  }, [hydrate]);

  const awake = power === "awake";

  async function toggle(next: PowerState) {
    if (busy || next === power || disabled) return;
    setBusy(true);
    try {
      const state = await setPowerState({ host, token }, next, deviceId);
      setPower(state);
    } finally {
      setBusy(false);
    }
  }

  return (
    <main className="flex min-h-dvh flex-col">
      <ScreenHeader title="Power" subtitle="Wake or rest the host" />

      <div className="mx-auto flex w-full max-w-md flex-1 flex-col items-center px-5 pb-28">
        <div className="my-8">
          <PresenceOrb
            mood={busy ? "thinking" : awake ? "awake" : "sleeping"}
            size="h-40 w-40"
          />
        </div>

        <p className="text-center text-lg font-medium">
          {busy
            ? awake
              ? "Winding down…"
              : "Waking up…"
            : awake
              ? "Miori is awake"
              : "Miori is sleeping"}
        </p>
        <p className="mt-1 max-w-xs text-center text-sm text-ink-soft">
          {awake
            ? "She's listening and ready on the host."
            : "The host is idling quietly. Wake her whenever you need her."}
        </p>

        {/* Segmented toggle */}
        <GlassCard elevated className="mt-8 w-full p-1.5">
          <div className="grid grid-cols-2 gap-1.5">
            <ToggleButton
              active={awake}
              busy={busy && awake}
              disabled={disabled}
              onClick={() => toggle("awake")}
              icon={<Sun className="h-5 w-5" aria-hidden />}
              label="Wake"
            />
            <ToggleButton
              active={!awake}
              busy={busy && !awake}
              disabled={disabled}
              onClick={() => toggle("sleeping")}
              icon={<Moon className="h-5 w-5" aria-hidden />}
              label="Sleep"
              tone="rest"
            />
          </div>
        </GlassCard>

        {disabled && (
          <p className="mt-5 flex items-start gap-2 rounded-xl border border-warn/25 bg-warn/[0.06] px-4 py-2.5 text-left text-xs text-warn">
            <CircleSlash className="mt-0.5 h-4 w-4 shrink-0" aria-hidden />
            <span>
              Remote control is off on this host. Restart the backend with{" "}
              <code className="font-mono">REMOTE_ENABLED=true</code> to wake or
              sleep devices from here.
            </span>
          </p>
        )}
      </div>
    </main>
  );
}

function ToggleButton({
  active,
  busy,
  disabled,
  onClick,
  icon,
  label,
  tone = "wake",
}: {
  active: boolean;
  busy: boolean;
  disabled?: boolean;
  onClick: () => void;
  icon: React.ReactNode;
  label: string;
  tone?: "wake" | "rest";
}) {
  return (
    <Button
      variant="subtle"
      size="lg"
      loading={busy}
      disabled={disabled}
      onClick={onClick}
      className={cn(
        "h-16 flex-col gap-1 rounded-xl text-sm",
        active
          ? tone === "wake"
            ? "bg-accent/15 text-accent-soft"
            : "bg-white/[0.06] text-ink"
          : "text-ink-faint",
      )}
    >
      {!busy && icon}
      {label}
    </Button>
  );
}

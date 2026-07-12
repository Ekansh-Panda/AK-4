import {
  createContext,
  useContext,
  useEffect,
  useMemo,
  useRef,
  useState,
  useCallback,
  type ReactNode,
} from "react";
import type { PresenceState } from "@/lib/types";

interface PresenceContextValue {
  presence: PresenceState;
  setPresence: (p: PresenceState) => void;
}

const PresenceContext = createContext<PresenceContextValue | null>(null);

// The presence/status bus lives on its own socket (/ws/status). Do NOT reuse
// VITE_MIORI_WS — that points at the chat socket (/ws/chat). Derive the status
// URL from the API origin so it tracks VITE_MIORI_API in every environment.
const WS_STATUS_URL =
  (import.meta.env.VITE_MIORI_WS_STATUS as string | undefined) ??
  (() => {
    const api =
      (import.meta.env.VITE_MIORI_API as string | undefined) ??
      "http://localhost:8000/api";
    const origin = api.replace(/\/api\/?$/, "");
    return origin.replace(/^http/, "ws") + "/ws/status";
  })();

function statusToPresence(data: Record<string, unknown>): PresenceState | null {
  const type = data.type as string | undefined;
  switch (type) {
    case "heartbeat":
      return null;
    case "task":
    case "research": {
      const status = String(data.status ?? "").toLowerCase();
      if (["running", "started", "pending"].includes(status)) return "thinking";
      if (["done", "completed", "finished", "cancelled", "canceled"].includes(status)) return "idle";
      return null;
    }
    case "tool_approval":
    case "step_approval_needed":
      return "thinking";
    default:
      return null;
  }
}

export function PresenceProvider({ children }: { children: ReactNode }) {
  const [presence, setPresence] = useState<PresenceState>("idle");
  const wsRef = useRef<WebSocket | null>(null);
  const closedRef = useRef(false);
  const presenceRef = useRef<PresenceState>("idle");
  presenceRef.current = presence;

  const connect = useCallback(() => {
    if (closedRef.current) return;
    try {
      const ws = new WebSocket(WS_STATUS_URL);
      wsRef.current = ws;

      ws.onopen = () => {
        if (presenceRef.current === "error") {
          setPresence("idle");
        }
      };

      ws.onmessage = (ev) => {
        try {
          const data = JSON.parse(ev.data as string) as Record<string, unknown>;
          const next = statusToPresence(data);
          if (next) setPresence(next);
        } catch {
          // ignore malformed frames
        }
      };

      ws.onerror = () => {
        setPresence("error");
      };

      ws.onclose = () => {
        setPresence("error");
        wsRef.current = null;
        if (!closedRef.current) {
          setTimeout(() => connect(), 3000);
        }
      };
    } catch {
      // Can't create socket — stay idle.
    }
  }, []);

  useEffect(() => {
    closedRef.current = false;
    connect();
    return () => {
      closedRef.current = true;
      const ws = wsRef.current;
      if (ws) {
        ws.onclose = null;
        ws.close();
        wsRef.current = null;
      }
    };
  }, [connect]);

  const value = useMemo(() => ({ presence, setPresence }), [presence]);

  return (
    <PresenceContext.Provider value={value}>{children}</PresenceContext.Provider>
  );
}

export function usePresence(): PresenceContextValue {
  const ctx = useContext(PresenceContext);
  if (!ctx) throw new Error("usePresence must be used within PresenceProvider");
  return ctx;
}

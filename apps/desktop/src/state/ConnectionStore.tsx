import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useRef,
  useState,
  type ReactNode,
} from "react";
import type {
  ApiHealth,
  ApiProviderStatus,
  ConnectionStatus,
  ContextSnapshot,
} from "@/lib/types";
import { api } from "@/lib/api";
import { mockContext } from "@/lib/mockData";

interface ConnectionContextValue {
  status: ConnectionStatus;
  /** Aggregate right-panel context (model, tools, memory hits, devices, persona). */
  context: ContextSnapshot;
  /** Parsed /health payload when connected (null when offline / down). */
  health: ApiHealth | null;
  /** Per-provider status from GET /providers/status. */
  providers: ApiProviderStatus[];
  /** Name of the active provider (drives the active-model indicator). */
  activeProvider: string | null;
  refresh: () => void;
}

const ConnectionContext = createContext<ConnectionContextValue | null>(null);

/** Polite polling: 15s when connected, backing off to 30s when offline. */
const POLL_OK_MS = 15_000;
const POLL_DOWN_MS = 30_000;

export function ConnectionProvider({ children }: { children: ReactNode }) {
  const [status, setStatus] = useState<ConnectionStatus>("connecting");
  const [context, setContext] = useState<ContextSnapshot>(mockContext);
  const [health, setHealth] = useState<ApiHealth | null>(null);
  const [providers, setProviders] = useState<ApiProviderStatus[]>([]);

  const timer = useRef<ReturnType<typeof setTimeout> | null>(null);
  const inFlight = useRef(false);

  const poll = useCallback(async () => {
    if (inFlight.current) return;
    inFlight.current = true;
    try {
      const h = await api.getHealth();
      setHealth(h);
      const online = h !== null;
      setStatus(online ? "connected" : "offline");

      // Only fan out the heavier reads when the server is actually up; this
      // avoids 3 timeouts per cycle while offline (no tight loops).
      if (online) {
        const [statuses, ctx] = await Promise.all([
          api.providerStatus(),
          api.getContext(),
        ]);
        setProviders(statuses.ok ? statuses.data : []);
        setContext(ctx);
      } else {
        setProviders([]);
        setContext(mockContext);
      }

      // Schedule the next poll with a politeness-aware interval.
      if (timer.current) clearTimeout(timer.current);
      timer.current = setTimeout(
        () => void poll(),
        online ? POLL_OK_MS : POLL_DOWN_MS,
      );
    } finally {
      inFlight.current = false;
    }
  }, []);

  const refresh = useCallback(() => {
    setStatus("connecting");
    if (timer.current) clearTimeout(timer.current);
    void poll();
  }, [poll]);

  useEffect(() => {
    void poll();
    return () => {
      if (timer.current) clearTimeout(timer.current);
    };
  }, [poll]);

  const activeProvider = useMemo(
    () => providers.find((p) => p.active)?.name ?? null,
    [providers],
  );

  const value = useMemo<ConnectionContextValue>(
    () => ({ status, context, health, providers, activeProvider, refresh }),
    [status, context, health, providers, activeProvider, refresh],
  );

  return (
    <ConnectionContext.Provider value={value}>{children}</ConnectionContext.Provider>
  );
}

export function useConnection(): ConnectionContextValue {
  const ctx = useContext(ConnectionContext);
  if (!ctx) throw new Error("useConnection must be used within ConnectionProvider");
  return ctx;
}

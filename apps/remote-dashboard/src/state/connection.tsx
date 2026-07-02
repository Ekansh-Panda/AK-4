/**
 * Connection context — holds the host address, token, theme, and live
 * connection status for the whole app. Persists host/token/theme to
 * localStorage so a returning phone reconnects with one tap.
 *
 * The token is stored in plain localStorage. That's acceptable for a
 * LAN-only, single-purpose pairing token (see README security note), but it is
 * NOT a place for long-lived secrets.
 */
import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from "react";
import { connect as apiConnect, resetSession } from "@/lib/api";
import type {
  Connection,
  ConnectionStatus,
  ThemeMode,
} from "@/lib/types";

const STORAGE_KEY = "miori.remote.connection.v1";
const THEME_KEY = "miori.remote.theme.v1";

interface PersistShape {
  host: string;
  token: string;
}

interface ConnectionContextValue {
  host: string;
  token: string;
  status: ConnectionStatus;
  hostName?: string;
  version?: string;
  error?: string;
  theme: ThemeMode;

  /** True once a successful connect has happened this session. */
  isConnected: boolean;
  /** True when the live host has the remote module enabled (device/power). */
  remoteEnabled: boolean;
  /** True when the session is running against the offline mock fallback. */
  isMock: boolean;

  setHost: (host: string) => void;
  setToken: (token: string) => void;
  setTheme: (theme: ThemeMode) => void;

  /** Attempt to connect with the given (or current) credentials. */
  connect: (next?: Partial<Connection>) => Promise<boolean>;
  /** Drop the session (keeps stored host/token for convenience). */
  disconnect: () => void;
}

const ConnectionContext = createContext<ConnectionContextValue | null>(null);

function loadPersisted(): PersistShape {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (raw) return JSON.parse(raw) as PersistShape;
  } catch {
    /* ignore malformed storage */
  }
  return { host: "", token: "" };
}

function loadTheme(): ThemeMode {
  const t = localStorage.getItem(THEME_KEY);
  return t === "dusk" ? "dusk" : "dark";
}

export function ConnectionProvider({ children }: { children: ReactNode }) {
  const persisted = loadPersisted();
  const [host, setHost] = useState(persisted.host);
  const [token, setToken] = useState(persisted.token);
  const [theme, setThemeState] = useState<ThemeMode>(loadTheme);
  const [status, setStatus] = useState<ConnectionStatus>("disconnected");
  const [hostName, setHostName] = useState<string>();
  const [version, setVersion] = useState<string>();
  const [error, setError] = useState<string>();
  const [remoteEnabled, setRemoteEnabled] = useState(false);
  const [isMock, setIsMock] = useState(false);

  // Persist host/token whenever they change.
  useEffect(() => {
    const data: PersistShape = { host, token };
    localStorage.setItem(STORAGE_KEY, JSON.stringify(data));
  }, [host, token]);

  // Apply + persist theme by toggling the `theme-dusk` class on <html>.
  useEffect(() => {
    const root = document.documentElement;
    root.classList.toggle("theme-dusk", theme === "dusk");
    localStorage.setItem(THEME_KEY, theme);
  }, [theme]);

  const setTheme = useCallback((next: ThemeMode) => setThemeState(next), []);

  const connect = useCallback(
    async (next?: Partial<Connection>): Promise<boolean> => {
      const conn: Connection = {
        host: (next?.host ?? host).trim(),
        token: (next?.token ?? token).trim(),
      };
      // Reflect any inline overrides into state so fields stay in sync.
      if (next?.host !== undefined) setHost(conn.host);
      if (next?.token !== undefined) setToken(conn.token);

      setStatus("connecting");
      setError(undefined);
      // A fresh connection starts a fresh server-side chat session.
      resetSession();
      const result = await apiConnect(conn);
      if (result.ok) {
        setHostName(result.hostName);
        setVersion(result.version);
        setRemoteEnabled(result.remoteEnabled ?? false);
        setIsMock(Boolean(result.isMock));
        setStatus("connected");
        return true;
      }
      setError(result.error ?? "Connection failed.");
      setStatus("error");
      return false;
    },
    [host, token],
  );

  const disconnect = useCallback(() => {
    setStatus("disconnected");
    setHostName(undefined);
    setVersion(undefined);
    setError(undefined);
    setRemoteEnabled(false);
    setIsMock(false);
    resetSession();
  }, []);

  const value = useMemo<ConnectionContextValue>(
    () => ({
      host,
      token,
      status,
      hostName,
      version,
      error,
      theme,
      isConnected: status === "connected",
      remoteEnabled,
      isMock,
      setHost,
      setToken,
      setTheme,
      connect,
      disconnect,
    }),
    [
      host,
      token,
      status,
      hostName,
      version,
      error,
      theme,
      remoteEnabled,
      isMock,
      connect,
      disconnect,
      setTheme,
    ],
  );

  return (
    <ConnectionContext.Provider value={value}>
      {children}
    </ConnectionContext.Provider>
  );
}

export function useConnection(): ConnectionContextValue {
  const ctx = useContext(ConnectionContext);
  if (!ctx) {
    throw new Error("useConnection must be used within a ConnectionProvider");
  }
  return ctx;
}

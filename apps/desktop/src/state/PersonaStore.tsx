import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from "react";
import type { ApiPersona, PersonaMode } from "@/lib/types";
import { api } from "@/lib/api";

export interface PersonaDescriptor {
  mode: PersonaMode;
  label: string;
  blurb: string;
}

/** Local UI "mood" presets that drive the orb + status badge feel. */
export const PERSONA_MODES: PersonaDescriptor[] = [
  { mode: "warm", label: "Warm", blurb: "Friendly, present, a little tender." },
  { mode: "focused", label: "Focused", blurb: "Direct and economical. Less small talk." },
  { mode: "playful", label: "Playful", blurb: "Light, teasing, quick-witted." },
  { mode: "quiet", label: "Quiet", blurb: "Minimal words. Only speaks when it helps." },
];

interface PersonaContextValue {
  /** Local UI mood preset (orb / badge feel). */
  mode: PersonaMode;
  setMode: (mode: PersonaMode) => void;
  descriptor: PersonaDescriptor;
  /** Backend persona config from GET /persona (null while loading / offline). */
  persona: ApiPersona | null;
  /** Available backend persona modes (GET /persona/modes). */
  backendModes: string[];
  /** The backend's active persona mode (what chat actually uses). */
  backendMode: string | null;
  /** POST /persona/mode {mode} and refresh local persona state. */
  setBackendMode: (mode: string) => Promise<void>;
  /** Re-fetch persona + modes from the backend. */
  refreshPersona: () => void;
}

const PersonaContext = createContext<PersonaContextValue | null>(null);

export function PersonaProvider({ children }: { children: ReactNode }) {
  const [mode, setMode] = useState<PersonaMode>("warm");
  const [persona, setPersona] = useState<ApiPersona | null>(null);
  const [backendModes, setBackendModes] = useState<string[]>([]);

  const refreshPersona = useCallback(() => {
    void api.getPersona().then((r) => setPersona(r.data));
    void api.personaModes().then((r) => setBackendModes(r.ok ? r.data : []));
  }, []);

  useEffect(() => {
    refreshPersona();
  }, [refreshPersona]);

  const setBackendMode = useCallback(async (next: string) => {
    const r = await api.setPersonaMode(next);
    if (r.ok && r.data) setPersona(r.data);
  }, []);

  const value = useMemo<PersonaContextValue>(() => {
    const descriptor =
      PERSONA_MODES.find((p) => p.mode === mode) ?? PERSONA_MODES[0];
    return {
      mode,
      setMode,
      descriptor,
      persona,
      backendModes,
      backendMode: persona?.active_mode ?? null,
      setBackendMode,
      refreshPersona,
    };
  }, [mode, persona, backendModes, setBackendMode, refreshPersona]);

  return <PersonaContext.Provider value={value}>{children}</PersonaContext.Provider>;
}

export function usePersona(): PersonaContextValue {
  const ctx = useContext(PersonaContext);
  if (!ctx) throw new Error("usePersona must be used within PersonaProvider");
  return ctx;
}

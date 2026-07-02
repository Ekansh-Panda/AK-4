import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useReducer,
  useRef,
  type ReactNode,
} from "react";
import type { ApiMessage, ChatMessage, PresenceState, Role } from "@/lib/types";
import { mockMessages, uid } from "@/lib/mockData";
import { streamChat } from "@/lib/ws";
import { api } from "@/lib/api";
import { usePersona } from "@/state/PersonaStore";

interface ChatState {
  messages: ChatMessage[];
  presence: PresenceState;
  /** Active backend session id (null until created / loaded). */
  sessionId: string | null;
}

type Action =
  | { type: "add"; message: ChatMessage }
  | { type: "appendChunk"; id: string; chunk: string }
  | { type: "finish"; id: string }
  | { type: "presence"; presence: PresenceState }
  | { type: "session"; sessionId: string }
  | { type: "hydrate"; messages: ChatMessage[] }
  | { type: "clear" };

/** Backend role -> UI role ("assistant" becomes "miori"). */
function roleFromApi(role: string): Role {
  if (role === "user") return "user";
  if (role === "system") return "system";
  return "miori";
}

function messageFromApi(m: ApiMessage): ChatMessage {
  return {
    id: m.id,
    role: roleFromApi(m.role),
    content: m.content,
    createdAt: Date.parse(m.created_at) || Date.now(),
  };
}

function reducer(state: ChatState, action: Action): ChatState {
  switch (action.type) {
    case "add":
      return { ...state, messages: [...state.messages, action.message] };
    case "appendChunk":
      return {
        ...state,
        messages: state.messages.map((m) =>
          m.id === action.id ? { ...m, content: m.content + action.chunk } : m,
        ),
      };
    case "finish":
      return {
        ...state,
        messages: state.messages.map((m) =>
          m.id === action.id ? { ...m, streaming: false } : m,
        ),
      };
    case "presence":
      return { ...state, presence: action.presence };
    case "session":
      return { ...state, sessionId: action.sessionId };
    case "hydrate":
      return { ...state, messages: action.messages };
    case "clear":
      return { ...state, messages: [], sessionId: null };
    default:
      return state;
  }
}

interface ChatContextValue extends ChatState {
  send: (content: string) => void;
  clear: () => void;
}

const ChatContext = createContext<ChatContextValue | null>(null);

export function ChatProvider({ children }: { children: ReactNode }) {
  const { backendMode } = usePersona();
  const [state, dispatch] = useReducer(reducer, {
    messages: mockMessages,
    presence: "idle",
    sessionId: null,
  });

  // Keep the latest session id in a ref so `send` stays stable yet current.
  const sessionRef = useRef<string | null>(null);
  sessionRef.current = state.sessionId;
  const personaRef = useRef<string | null>(backendMode);
  personaRef.current = backendMode;

  // On mount, try to create a real session and load any history. On failure the
  // mock greeting from `mockMessages` stays in place (offline-friendly).
  useEffect(() => {
    let cancelled = false;
    void (async () => {
      const created = await api.createSession();
      if (cancelled || !created.ok || !created.data) return;
      dispatch({ type: "session", sessionId: created.data.id });
      const history = await api.sessionMessages(created.data.id);
      if (cancelled) return;
      if (history.ok && history.data.length) {
        dispatch({ type: "hydrate", messages: history.data.map(messageFromApi) });
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  const send = useCallback((content: string) => {
    const trimmed = content.trim();
    if (!trimmed) return;

    dispatch({
      type: "add",
      message: { id: uid("msg"), role: "user", content: trimmed, createdAt: Date.now() },
    });

    const replyId = uid("msg");
    dispatch({
      type: "add",
      message: {
        id: replyId,
        role: "miori",
        content: "",
        createdAt: Date.now(),
        streaming: true,
      },
    });
    dispatch({ type: "presence", presence: "thinking" });

    streamChat(
      trimmed,
      {
        onSession: (sid) => dispatch({ type: "session", sessionId: sid }),
        onChunk: (chunk) => {
          dispatch({ type: "presence", presence: "speaking" });
          dispatch({ type: "appendChunk", id: replyId, chunk });
        },
        onDone: (sid) => {
          if (sid) dispatch({ type: "session", sessionId: sid });
          dispatch({ type: "finish", id: replyId });
          dispatch({ type: "presence", presence: "idle" });
        },
        onError: () => {
          dispatch({ type: "finish", id: replyId });
          dispatch({ type: "presence", presence: "idle" });
        },
      },
      {
        sessionId: sessionRef.current ?? undefined,
        personaMode: personaRef.current ?? undefined,
      },
    );
  }, []);

  const clear = useCallback(() => dispatch({ type: "clear" }), []);

  return (
    <ChatContext.Provider value={{ ...state, send, clear }}>
      {children}
    </ChatContext.Provider>
  );
}

export function useChat(): ChatContextValue {
  const ctx = useContext(ChatContext);
  if (!ctx) throw new Error("useChat must be used within ChatProvider");
  return ctx;
}

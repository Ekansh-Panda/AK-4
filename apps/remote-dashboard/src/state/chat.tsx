/**
 * Chat context — holds the remote conversation with Miori and drives the mock
 * streaming reply. Kept deliberately simple: an in-memory message list plus a
 * `send` action. History is not persisted (a fresh phone session starts clean).
 */
import {
  createContext,
  useCallback,
  useContext,
  useMemo,
  useRef,
  useState,
  type ReactNode,
} from "react";
import { sendMessage as apiSendMessage } from "@/lib/api";
import { MOCK_GREETING } from "@/lib/mock";
import type { ChatMessage } from "@/lib/types";
import { useConnection } from "./connection";

interface ChatContextValue {
  messages: ChatMessage[];
  /** True while Miori's reply is streaming in. */
  isSending: boolean;
  send: (text: string) => Promise<void>;
  clear: () => void;
}

const ChatContext = createContext<ChatContextValue | null>(null);

function uid(): string {
  return Math.random().toString(36).slice(2) + Date.now().toString(36);
}

function greeting(): ChatMessage {
  return { id: uid(), role: "miori", content: MOCK_GREETING, at: Date.now() };
}

export function ChatProvider({ children }: { children: ReactNode }) {
  const { host, token } = useConnection();
  const [messages, setMessages] = useState<ChatMessage[]>(() => [greeting()]);
  const [isSending, setIsSending] = useState(false);
  const abortRef = useRef<AbortController | null>(null);

  const send = useCallback(
    async (text: string) => {
      const trimmed = text.trim();
      if (!trimmed || isSending) return;

      const userMsg: ChatMessage = {
        id: uid(),
        role: "user",
        content: trimmed,
        at: Date.now(),
      };
      const replyId = uid();
      const replyMsg: ChatMessage = {
        id: replyId,
        role: "miori",
        content: "",
        at: Date.now(),
        streaming: true,
      };
      setMessages((prev) => [...prev, userMsg, replyMsg]);
      setIsSending(true);

      const controller = new AbortController();
      abortRef.current = controller;

      try {
        await apiSendMessage(
          { host, token },
          trimmed,
          (delta) => {
            setMessages((prev) =>
              prev.map((m) =>
                m.id === replyId ? { ...m, content: m.content + delta } : m,
              ),
            );
          },
          controller.signal,
        );
      } catch {
        setMessages((prev) =>
          prev.map((m) =>
            m.id === replyId
              ? {
                  ...m,
                  content:
                    m.content ||
                    "I couldn't reach the host just now. Check the connection and try again.",
                }
              : m,
          ),
        );
      } finally {
        setMessages((prev) =>
          prev.map((m) => (m.id === replyId ? { ...m, streaming: false } : m)),
        );
        setIsSending(false);
        abortRef.current = null;
      }
    },
    [host, token, isSending],
  );

  const clear = useCallback(() => {
    abortRef.current?.abort();
    setMessages([greeting()]);
    setIsSending(false);
  }, []);

  const value = useMemo<ChatContextValue>(
    () => ({ messages, isSending, send, clear }),
    [messages, isSending, send, clear],
  );

  return <ChatContext.Provider value={value}>{children}</ChatContext.Provider>;
}

export function useChat(): ChatContextValue {
  const ctx = useContext(ChatContext);
  if (!ctx) throw new Error("useChat must be used within a ChatProvider");
  return ctx;
}

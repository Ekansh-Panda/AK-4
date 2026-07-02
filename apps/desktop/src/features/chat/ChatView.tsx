import { useEffect, useRef } from "react";
import { motion } from "framer-motion";
import { Avatar } from "@/components/ui/Avatar";
import { ScrollArea } from "@/components/ui/ScrollArea";
import { StatusBadge } from "@/components/ui/StatusBadge";
import { Composer } from "@/components/layout/Composer";
import { useChat } from "@/state/ChatStore";
import { useConnection } from "@/state/ConnectionStore";
import { usePersona } from "@/state/PersonaStore";
import { cn } from "@/lib/cn";
import type { ChatMessage } from "@/lib/types";

function TypingDots() {
  return (
    <span className="inline-flex items-center gap-1 align-middle">
      {[0, 1, 2].map((i) => (
        <motion.span
          key={i}
          className="h-1.5 w-1.5 rounded-full bg-accent/70"
          animate={{ opacity: [0.3, 1, 0.3], y: [0, -2, 0] }}
          transition={{ duration: 1, repeat: Infinity, delay: i * 0.15 }}
        />
      ))}
    </span>
  );
}

function Bubble({ message }: { message: ChatMessage }) {
  const isUser = message.role === "user";
  const empty = message.streaming && message.content.length === 0;

  return (
    <motion.div
      initial={{ opacity: 0, y: 6 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3, ease: [0.22, 1, 0.36, 1] }}
      className={cn("flex gap-3", isUser ? "flex-row-reverse" : "flex-row")}
    >
      <Avatar who={isUser ? "user" : "miori"} size={30} className="mt-1" />
      <div
        className={cn(
          "max-w-[72%] rounded-lg px-4 py-2.5 text-sm leading-relaxed",
          isUser
            ? "bg-accent/15 text-ink border border-accent/20"
            : "glass-soft text-ink",
        )}
      >
        {empty ? <TypingDots /> : <span className="whitespace-pre-wrap">{message.content}</span>}
      </div>
    </motion.div>
  );
}

export function ChatView() {
  const { messages, send } = useChat();
  const { activeProvider, status } = useConnection();
  const { descriptor, backendMode } = usePersona();
  const endRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const personaLabel = backendMode ?? descriptor.label;

  return (
    <div className="mx-auto flex h-full max-w-3xl flex-col px-6">
      {/* Live persona + active provider indicators (graceful when offline). */}
      <div className="flex items-center justify-center gap-2 pt-4">
        <StatusBadge label={`Persona · ${personaLabel}`} tone="accent" />
        <StatusBadge
          label={
            status === "connected" && activeProvider
              ? `Provider · ${activeProvider}`
              : "Provider · mock"
          }
          tone={status === "connected" && activeProvider ? "positive" : "muted"}
        />
      </div>

      <ScrollArea className="flex-1 py-6">
        <div className="space-y-5">
          {messages.map((m) => (
            <Bubble key={m.id} message={m} />
          ))}
          <div ref={endRef} />
        </div>
      </ScrollArea>

      <div className="pb-5 pt-2">
        <Composer onSend={send} />
        <p className="mt-2 text-center text-[0.65rem] text-ink-faint">
          Enter to send · Shift+Enter for a new line
        </p>
      </div>
    </div>
  );
}

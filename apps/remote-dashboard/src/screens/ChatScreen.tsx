import { useEffect, useRef, useState, type FormEvent } from "react";
import { SendHorizonal, Eraser } from "lucide-react";
import { cn } from "@/lib/cn";
import { Button } from "@/components/Button";
import { ConnectionChip } from "@/components/ConnectionChip";
import { useChat } from "@/state/chat";
import type { ChatMessage } from "@/lib/types";

/** Remote chat with Miori. Mock streaming reply via the chat context. */
export function ChatScreen() {
  const { messages, isSending, send, clear } = useChat();
  const [draft, setDraft] = useState("");
  const scrollRef = useRef<HTMLDivElement>(null);

  // Keep the latest message in view as the reply streams in.
  useEffect(() => {
    scrollRef.current?.scrollTo({
      top: scrollRef.current.scrollHeight,
      behavior: "smooth",
    });
  }, [messages]);

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    const text = draft;
    setDraft("");
    await send(text);
  }

  return (
    <div className="flex h-dvh flex-col">
      {/* Header */}
      <header className="sticky top-0 z-20 flex items-center justify-between gap-3 px-4 pt-safe">
        <div className="flex items-center gap-3 py-3">
          <h1 className="text-lg font-semibold tracking-tight">Miori</h1>
          <ConnectionChip />
        </div>
        <button
          onClick={clear}
          className="flex h-9 items-center gap-1.5 rounded-full px-3 text-xs text-ink-faint transition-colors hover:text-ink-soft"
          aria-label="Clear conversation"
        >
          <Eraser className="h-3.5 w-3.5" aria-hidden />
          Clear
        </button>
      </header>

      {/* Messages */}
      <div
        ref={scrollRef}
        className="no-scrollbar flex-1 overflow-y-auto px-4 py-3"
      >
        <div className="mx-auto flex max-w-md flex-col gap-3">
          {messages.map((m) => (
            <Bubble key={m.id} message={m} />
          ))}
        </div>
      </div>

      {/* Composer */}
      <form
        onSubmit={onSubmit}
        className="px-3 pb-2 pb-safe pl-safe pr-safe"
      >
        <div className="mx-auto flex max-w-md items-end gap-2">
          <div className="glass-elevated flex flex-1 items-center rounded-2xl px-1.5 py-1.5">
            <input
              className="flex-1 bg-transparent px-3 py-2.5 text-base text-ink placeholder:text-ink-faint outline-none"
              placeholder="Say something to Miori…"
              value={draft}
              onChange={(e) => setDraft(e.target.value)}
              enterKeyHint="send"
              autoComplete="off"
            />
          </div>
          <Button
            type="submit"
            size="lg"
            className="h-12 w-12 shrink-0 rounded-2xl px-0"
            loading={isSending}
            disabled={!draft.trim()}
            aria-label="Send"
          >
            {!isSending && <SendHorizonal className="h-5 w-5" aria-hidden />}
          </Button>
        </div>
      </form>
    </div>
  );
}

function Bubble({ message }: { message: ChatMessage }) {
  const isUser = message.role === "user";
  const empty = message.streaming && message.content.length === 0;

  return (
    <div
      className={cn(
        "flex animate-fade-up",
        isUser ? "justify-end" : "justify-start",
      )}
    >
      <div
        className={cn(
          "max-w-[82%] rounded-2xl px-4 py-2.5 text-[15px] leading-relaxed",
          isUser
            ? "bg-accent text-canvas rounded-br-md"
            : "glass text-ink rounded-bl-md",
        )}
      >
        {empty ? (
          <TypingDots />
        ) : (
          <span className="whitespace-pre-wrap">
            {message.content}
            {message.streaming && (
              <span className="ml-0.5 inline-block h-4 w-[2px] translate-y-0.5 animate-blink bg-current align-middle" />
            )}
          </span>
        )}
      </div>
    </div>
  );
}

function TypingDots() {
  return (
    <span className="flex items-center gap-1 py-1">
      {[0, 1, 2].map((i) => (
        <span
          key={i}
          className="h-1.5 w-1.5 animate-blink rounded-full bg-ink-soft"
          style={{ animationDelay: `${i * 0.18}s` }}
        />
      ))}
    </span>
  );
}

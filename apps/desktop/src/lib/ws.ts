import { mockReply } from "./mockData";

/**
 * Chat websocket helper.
 *
 * When a real backend exists it connects to `ws://localhost:8000/ws/chat`
 * (services/core-api/app/ws/chat.py) and streams token frames. When it's
 * unreachable it falls back to a local mock that "types" a canned reply
 * chunk-by-chunk, so the streaming UX is fully exercised with no server.
 *
 * Frame protocol (server -> client):
 *   {"type":"session","session_id":"..."}
 *   {"type":"token","token":"..."}
 *   {"type":"done","session_id":"..."}
 *   {"type":"error","detail":"..."}
 */

const WS_URL =
  (import.meta.env.VITE_MIORI_WS as string | undefined) ??
  "ws://localhost:8000/ws/chat";

export interface ChatStreamOptions {
  /** Existing session to continue; the backend creates one if omitted. */
  sessionId?: string;
  /** Persona mode passed through to the backend (e.g. "friend"). */
  personaMode?: string;
  /** Optional model override. */
  model?: string;
}

export interface ChatStreamHandlers {
  /** Called for each streamed token/chunk. */
  onChunk: (chunk: string) => void;
  /** Called once when the reply is complete (carries final session id if any). */
  onDone: (sessionId?: string) => void;
  /** Called when the backend announces the session id for this turn. */
  onSession?: (sessionId: string) => void;
  onError?: (err: unknown) => void;
}

/** A handle you can call to abort an in-flight reply. */
export interface ChatStreamHandle {
  cancel: () => void;
}

/**
 * Send a prompt and stream the reply.
 * Tries a real websocket first; on failure, falls back to the local mock.
 */
export function streamChat(
  prompt: string,
  handlers: ChatStreamHandlers,
  options: ChatStreamOptions = {},
): ChatStreamHandle {
  let cancelled = false;

  // Attempt a real connection; gracefully degrade to mock on any issue.
  let socket: WebSocket | null = null;
  try {
    socket = new WebSocket(WS_URL);
  } catch {
    socket = null;
  }

  if (socket) {
    const ws = socket;
    let opened = false;
    let finalized = false;
    let lastSession = options.sessionId;

    const fallbackTimer = setTimeout(() => {
      if (!opened && !cancelled) {
        try {
          ws.close();
        } catch {
          /* noop */
        }
        runMock(prompt, handlers, () => cancelled);
      }
    }, 1500);

    ws.onopen = () => {
      opened = true;
      clearTimeout(fallbackTimer);
      // Backend reads `message`; session_id / persona_mode / model are optional.
      ws.send(
        JSON.stringify({
          message: prompt,
          session_id: options.sessionId,
          persona_mode: options.personaMode,
          model: options.model,
        }),
      );
    };
    ws.onmessage = (ev) => {
      if (cancelled) return;
      try {
        const data = JSON.parse(ev.data as string) as {
          type: "session" | "token" | "done" | "error";
          token?: string;
          session_id?: string;
          detail?: string;
        };
        if (data.type === "session" && data.session_id) {
          lastSession = data.session_id;
          handlers.onSession?.(data.session_id);
        } else if (data.type === "token" && data.token) {
          handlers.onChunk(data.token);
        } else if (data.type === "error") {
          finalized = true;
          handlers.onError?.(new Error(data.detail ?? "chat error"));
          ws.close();
        } else if (data.type === "done") {
          if (data.session_id) lastSession = data.session_id;
          finalized = true;
          handlers.onDone(lastSession);
          ws.close();
        }
      } catch (err) {
        handlers.onError?.(err);
      }
    };
    ws.onerror = () => {
      clearTimeout(fallbackTimer);
      if (!opened && !cancelled) {
        runMock(prompt, handlers, () => cancelled);
      }
    };
    ws.onclose = () => {
      clearTimeout(fallbackTimer);
      // If the socket closed mid-stream without a done/error frame, don't leave
      // the UI stuck in a streaming state — finalize gracefully.
      if (opened && !cancelled && !finalized) {
        finalized = true;
        handlers.onDone(lastSession);
      }
    };

    return {
      cancel: () => {
        cancelled = true;
        clearTimeout(fallbackTimer);
        try {
          ws.close();
        } catch {
          /* noop */
        }
      },
    };
  }

  // No socket at all — pure mock path.
  runMock(prompt, handlers, () => cancelled);
  return {
    cancel: () => {
      cancelled = true;
    },
  };
}

/** Locally "type out" the mock reply chunk-by-chunk. */
function runMock(
  _prompt: string,
  handlers: ChatStreamHandlers,
  isCancelled: () => boolean,
): void {
  const words = mockReply.split(" ");
  let i = 0;
  const tick = () => {
    if (isCancelled()) return;
    if (i >= words.length) {
      handlers.onDone(undefined);
      return;
    }
    handlers.onChunk((i === 0 ? "" : " ") + words[i]);
    i += 1;
    setTimeout(tick, 45 + Math.random() * 55);
  };
  // Small "thinking" delay before the first token.
  setTimeout(tick, 320);
}

export const wsUrl = WS_URL;

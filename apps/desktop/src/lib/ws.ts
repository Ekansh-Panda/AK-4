/**
 * Chat websocket helper.
 *
 * Connects to `ws://localhost:8000/ws/chat`
 * (services/core-api/app/ws/chat.py) and streams token frames. When the socket
 * is unreachable the stream reports an error (via `onError`) and finalizes —
 * there is no mock reply, so the UI shows an honest "not connected" state.
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
        reportDisconnected(handlers, () => cancelled);
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
        reportDisconnected(handlers, () => cancelled);
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

  // No socket at all — report a disconnected state (no mock reply).
  reportDisconnected(handlers, () => cancelled);
  return {
    cancel: () => {
      cancelled = true;
    },
  };
}

/** Report that the backend is unreachable, then finalize the stream cleanly. */
function reportDisconnected(
  handlers: ChatStreamHandlers,
  isCancelled: () => boolean,
): void {
  if (isCancelled()) return;
  handlers.onError?.(new Error("Not connected to the Miori backend."));
  handlers.onDone(undefined);
}

export const wsUrl = WS_URL;

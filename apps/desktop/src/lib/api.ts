import type {
  ApiChatResponse,
  ApiChatSession,
  ApiDevice,
  ApiFile,
  ApiFileDetail,
  ApiHealth,
  ApiMemory,
  ApiMemoryCreate,
  ApiMemoryUpdate,
  ApiMessage,
  ApiModelInfo,
  ApiPersona,
  ApiProviderInfo,
  ApiProviderStatus,
  ApiProject,
  ApiProjectCreate,
  ApiProjectUpdate,
  ApiRemoteSession,
  ApiResult,
  ApiSetting,
  ApiTask,
  ApiTaskCreate,
  ApiTaskUpdate,
  ContextSnapshot,
  FileItem,
  MemoryEntry,
  ModelInfo,
  TaskItem,
} from "./types";
import {
  mockContext,
  mockFiles,
  mockMemoryEntries,
  mockModels,
  mockTasks,
} from "./mockData";

/**
 * Typed fetch client for the Miori FastAPI backend
 * (services/core-api). Request/response shapes mirror app/schemas/*.py exactly.
 *
 * The backend stays OPTIONAL: every call falls back to mock data / empty
 * collections when the server is unreachable or returns a non-2xx, so the shell
 * never hard-crashes and remains usable offline. Set `VITE_MIORI_API` to
 * override the base URL (default http://localhost:8000/api).
 */
const BASE =
  (import.meta.env.VITE_MIORI_API as string | undefined) ??
  "http://localhost:8000/api";

/** Server root (health lives at /health, NOT under the /api prefix). */
const ORIGIN = BASE.replace(/\/api\/?$/, "");

/** Short timeout so offline mode falls back fast instead of hanging the UI. */
const TIMEOUT_MS = 2500;

/**
 * Core request with a discriminated result: `ok` tells callers whether the
 * backend actually answered (vs. the fallback being served), and `status`
 * surfaces HTTP codes like 413 (oversize upload). `fallback` is returned on any
 * network error, timeout, or non-2xx response.
 */
async function requestResult<T>(
  path: string,
  fallback: T,
  init?: RequestInit,
): Promise<ApiResult<T>> {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), TIMEOUT_MS);
  try {
    // Only set a JSON content-type when we're not sending FormData (the browser
    // must set the multipart boundary itself for uploads).
    const isForm =
      typeof FormData !== "undefined" && init?.body instanceof FormData;
    const res = await fetch(`${BASE}${path}`, {
      ...init,
      signal: controller.signal,
      headers: {
        ...(isForm ? {} : { "Content-Type": "application/json" }),
        ...(init?.headers ?? {}),
      },
    });
    if (!res.ok) {
      return { data: fallback, ok: false, status: res.status };
    }
    // 204 / empty body tolerance.
    const text = await res.text();
    const data = (text ? JSON.parse(text) : fallback) as T;
    return { data, ok: true, status: res.status };
  } catch {
    return { data: fallback, ok: false };
  } finally {
    clearTimeout(timer);
  }
}

const json = (body: unknown): RequestInit => ({ body: JSON.stringify(body) });

/* ----------------------------------------------------------------------------
 * Edge mappers — translate backend wire types into the UI-facing types so the
 * existing components/design keep working unchanged.
 * ------------------------------------------------------------------------- */

function modelFromApi(m: ApiModelInfo): ModelInfo {
  return {
    id: m.id,
    label: m.name,
    provider: m.provider,
    contextTokens: m.context_window ?? 0,
    local: m.provider.toLowerCase().includes("local") ||
      m.provider.toLowerCase().includes("llama") ||
      m.provider.toLowerCase().includes("ollama"),
  };
}

function kindFromApiFile(f: ApiFile): FileItem["kind"] {
  const ct = (f.content_type ?? "").toLowerCase();
  if (ct.startsWith("image/")) return "image";
  if (ct.startsWith("audio/")) return "audio";
  const ext = f.filename.split(".").pop()?.toLowerCase() ?? "";
  if (["png", "jpg", "jpeg", "gif", "webp", "svg"].includes(ext)) return "image";
  if (["mp3", "m4a", "wav", "ogg", "flac"].includes(ext)) return "audio";
  if (["pdf", "txt", "md", "doc", "docx"].includes(ext)) return "doc";
  return "other";
}

/** Map a backend file to the lightweight UI list item (used by mock fallback shape). */
function fileItemFromApi(f: ApiFile): FileItem {
  return {
    id: f.id,
    name: f.filename,
    size: f.size_bytes,
    kind: kindFromApiFile(f),
    uploadedAt: Date.parse(f.created_at) || Date.now(),
  };
}

function memoryEntryFromApi(m: ApiMemory): MemoryEntry {
  // The backend stores a flat `content` blob + namespace; the UI shows a
  // title/body/tags shape. Derive a friendly title from the first line.
  const lines = m.content.split("\n");
  const title = (lines[0] || m.namespace).slice(0, 80);
  const body = lines.length > 1 ? lines.slice(1).join("\n").trim() || m.content : m.content;
  return {
    id: m.id,
    title,
    body,
    tags: m.namespace && m.namespace !== "default" ? [m.namespace] : [],
    pinned: m.pinned,
    updatedAt: Date.parse(m.updated_at) || Date.now(),
  };
}

function taskItemFromApi(t: ApiTask): TaskItem {
  return {
    id: t.id,
    title: t.title,
    done: t.status === "done" || t.status === "completed",
    createdAt: Date.parse(t.created_at) || Date.now(),
  };
}

export const api = {
  /* --- Chat ------------------------------------------------------------- */

  /** POST /chat — single-turn (non-streaming) reply. Streaming lives in ws.ts. */
  sendChat: (body: {
    message: string;
    session_id?: string;
    persona_mode?: string;
    model?: string;
  }) =>
    requestResult<ApiChatResponse>(
      "/chat",
      {
        session_id: body.session_id ?? "",
        reply: {
          id: "",
          created_at: new Date().toISOString(),
          updated_at: new Date().toISOString(),
          session_id: body.session_id ?? "",
          role: "assistant",
          content: "",
          model: null,
        },
      },
      { method: "POST", ...json(body) },
    ),

  /** POST /chat/sessions — create (or fetch) a session. */
  createSession: (body: { title?: string; persona_mode?: string } = {}) =>
    requestResult<ApiChatSession | null>("/chat/sessions", null, {
      method: "POST",
      ...json({ title: body.title ?? "New chat", persona_mode: body.persona_mode ?? "friend" }),
    }),

  /** GET /chat/sessions/{id}/messages — full history for a session. */
  sessionMessages: (sessionId: string) =>
    requestResult<ApiMessage[]>(
      `/chat/sessions/${encodeURIComponent(sessionId)}/messages`,
      [],
    ),

  /* --- Memory ----------------------------------------------------------- */

  /** GET /memory?kind=&pinned=&limit= */
  listMemory: (opts: { kind?: string; pinned?: boolean; limit?: number } = {}) => {
    const params = new URLSearchParams();
    if (opts.kind) params.set("kind", opts.kind);
    if (typeof opts.pinned === "boolean") params.set("pinned", String(opts.pinned));
    if (opts.limit) params.set("limit", String(opts.limit));
    const qs = params.toString();
    return requestResult<ApiMemory[]>(`/memory${qs ? `?${qs}` : ""}`, []);
  },

  /** POST /memory */
  createMemory: (body: ApiMemoryCreate) =>
    requestResult<ApiMemory | null>("/memory", null, { method: "POST", ...json(body) }),

  /** PATCH /memory/{id} — toggle pinned and/or edit content. */
  updateMemory: (id: string, body: ApiMemoryUpdate) =>
    requestResult<ApiMemory | null>(`/memory/${encodeURIComponent(id)}`, null, {
      method: "PATCH",
      ...json(body),
    }),

  /** DELETE /memory/{id} */
  deleteMemory: (id: string) =>
    requestResult<{ status: string } | null>(`/memory/${encodeURIComponent(id)}`, null, {
      method: "DELETE",
    }),

  /* --- Files ------------------------------------------------------------ */

  /** GET /files — lightweight list. */
  listFiles: () => requestResult<ApiFile[]>("/files", []),

  /** GET /files/{id} — detail incl. extracted_text. */
  fileDetail: (id: string) =>
    requestResult<ApiFileDetail | null>(`/files/${encodeURIComponent(id)}`, null),

  /** GET /files/search?q= — search files using chunk-level or fallback matching. */
  searchFiles: (q: string) =>
    requestResult<ApiFile[]>(`/files/search?q=${encodeURIComponent(q)}`, []),

  /** POST /files — multipart upload. Returns 413 status on oversize. */
  uploadFile: (file: File) => {
    const form = new FormData();
    form.append("file", file, file.name);
    return requestResult<ApiFileDetail | null>("/files", null, {
      method: "POST",
      body: form,
    });
  },

  /** DELETE /files/{id} */
  deleteFile: (id: string) =>
    requestResult<{ status: string } | null>(`/files/${encodeURIComponent(id)}`, null, {
      method: "DELETE",
    }),

  /* --- Audio ------------------------------------------------------------ */

  /** POST /audio/transcribe — multipart upload, returns {text}. */
  transcribeAudio: (file: Blob) => {
    const form = new FormData();
    form.append("file", file, "audio.webm");
    return requestResult<{ text: string }>("/audio/transcribe", { text: "" }, {
      method: "POST",
      body: form,
    });
  },

  /* --- Tasks ------------------------------------------------------------ */

  /** GET /tasks */
  listTasks: () => requestResult<ApiTask[]>("/tasks", []),

  /** POST /tasks */
  createTask: (body: ApiTaskCreate) =>
    requestResult<ApiTask | null>("/tasks", null, { method: "POST", ...json(body) }),

  /** PATCH /tasks/{id} — toggle status / edit. */
  updateTask: (id: string, body: ApiTaskUpdate) =>
    requestResult<ApiTask | null>(`/tasks/${encodeURIComponent(id)}`, null, {
      method: "PATCH",
      ...json(body),
    }),

  /** DELETE /tasks/{id} */
  deleteTask: (id: string) =>
    requestResult<{ status: string } | null>(`/tasks/${encodeURIComponent(id)}`, null, {
      method: "DELETE",
    }),

  /* --- Persona ---------------------------------------------------------- */

  /** GET /persona */
  getPersona: () => requestResult<ApiPersona | null>("/persona", null),

  /** GET /persona/modes */
  personaModes: () => requestResult<string[]>("/persona/modes", []),

  /** POST /persona/mode {mode} */
  setPersonaMode: (mode: string) =>
    requestResult<ApiPersona | null>("/persona/mode", null, {
      method: "POST",
      ...json({ mode }),
    }),

  /* --- Providers -------------------------------------------------------- */

  /** GET /providers */
  listProviders: () => requestResult<ApiProviderInfo[]>("/providers", []),

  /** GET /providers/status */
  providerStatus: () => requestResult<ApiProviderStatus[]>("/providers/status", []),

  /** PUT /providers/active {name} */
  setActiveProvider: (name: string) =>
    requestResult<{ active: string } | null>("/providers/active", null, {
      method: "PUT",
      ...json({ name }),
    }),

  /** GET /providers/models — models for the active provider. */
  listProviderModels: () => requestResult<ApiModelInfo[]>("/providers/models", []),

  /* --- Settings --------------------------------------------------------- */

  /** GET /settings */
  listSettings: () => requestResult<ApiSetting[]>("/settings", []),

  /** GET /settings/{key} */
  getSetting: (key: string) =>
    requestResult<ApiSetting | null>(`/settings/${encodeURIComponent(key)}`, null),

  /** PUT /settings {key,value} */
  putSetting: (key: string, value: string | null) =>
    requestResult<ApiSetting | null>("/settings", null, {
      method: "PUT",
      ...json({ key, value }),
    }),

  /** DELETE /settings/{key} */
  deleteSetting: (key: string) =>
    requestResult<{ status: string } | null>(`/settings/${encodeURIComponent(key)}`, null, {
      method: "DELETE",
    }),

  /* --- Computer Use --- */

  armComputerUse: () =>
    requestResult<{ detail: string } | null>("/settings/computer-use/arm", null, {
      method: "POST",
    }),

  disarmComputerUse: () =>
    requestResult<{ detail: string } | null>("/settings/computer-use/disarm", null, {
      method: "POST",
    }),

  getComputerUseAudit: () =>
    requestResult<any[]>("/settings/computer-use/audit", []),

  /* --- Projects --------------------------------------------------------- */

  /** GET /projects */
  listProjects: (status?: string) => {
    const qs = status ? `?status=${encodeURIComponent(status)}` : "";
    return requestResult<ApiProject[]>(`/projects${qs}`, []);
  },

  /** POST /projects */
  createProject: (body: ApiProjectCreate) =>
    requestResult<ApiProject | null>("/projects", null, { method: "POST", ...json(body) }),

  /** PATCH /projects/{id} */
  updateProject: (id: string, body: ApiProjectUpdate) =>
    requestResult<ApiProject | null>(`/projects/${encodeURIComponent(id)}`, null, {
      method: "PATCH",
      ...json(body),
    }),

  /** DELETE /projects/{id} */
  deleteProject: (id: string) =>
    requestResult<any>(`/projects/${encodeURIComponent(id)}`, null, { method: "DELETE" }),

  /* --- Research --------------------------------------------------------- */

  /** GET /research */
  listResearch: () => requestResult<any[]>("/research", []),

  /** POST /research — launch a new session */
  createResearch: (query: string) =>
    requestResult<any>("/research", null, { method: "POST", ...json({ query }) }),

  /** GET /research/{id} */
  getResearch: (id: string) =>
    requestResult<any>(`/research/${encodeURIComponent(id)}`, null),

  /** DELETE /research/{id} */
  deleteResearch: (id: string) =>
    requestResult<any>(`/research/${encodeURIComponent(id)}`, null, { method: "DELETE" }),

  /* --- Provider Ping ---------------------------------------------------- */

  /** GET /providers/ping — concurrent reachability check. */
  pingProviders: () =>
    requestResult<Record<string, boolean>>("/providers/ping", {}),

  /* --- Remote ----------------------------------------------------------- */

  /** GET /remote/devices */
  listDevices: () => requestResult<ApiDevice[]>("/remote/devices", []),

  /** GET /remote/sessions */
  listRemoteSessions: () => requestResult<ApiRemoteSession[]>("/remote/sessions", []),

  /* --- UI-shaped convenience reads (mapped at the edge) ----------------- */

  /**
   * Aggregate context for the right panel. There is no single backend endpoint,
   * so this is composed client-side from providers + memory + devices, with a
   * full fallback to `mockContext` when the backend is down.
   */
  async getContext(): Promise<ContextSnapshot> {
    const [providers, memory, devices] = await Promise.all([
      this.listProviders(),
      this.listMemory({ limit: 5 }),
      this.listDevices(),
    ]);
    if (!providers.ok && !memory.ok && !devices.ok) return mockContext;

    const active =
      providers.data.find((p) => p.active) ?? providers.data[0];
    const activeModel = active?.models[0];
    const model: ModelInfo = activeModel
      ? modelFromApi(activeModel)
      : mockContext.model;

    return {
      model,
      tools: mockContext.tools, // no backend tools endpoint yet
      recentMemory: memory.ok
        ? memory.data.map((m) => ({
            id: m.id,
            snippet: m.content.split("\n")[0].slice(0, 120),
            source: m.namespace,
            score: m.pinned ? 1 : 0.6,
            recalledAt: Date.parse(m.updated_at) || Date.now(),
          }))
        : mockContext.recentMemory,
      devices: devices.ok
        ? devices.data.map((d) => ({
            id: d.id,
            name: d.name,
            platform: ((): "windows" | "linux" | "macos" | "web" => {
              const p = (d.platform ?? "").toLowerCase();
              if (p.includes("win")) return "windows";
              if (p.includes("mac") || p.includes("darwin")) return "macos";
              if (p.includes("linux")) return "linux";
              return "web";
            })(),
            online: d.state === "online",
            lastSeen: d.last_seen_at ? Date.parse(d.last_seen_at) : Date.now(),
          }))
        : mockContext.devices,
      persona: mockContext.persona,
    };
  },

  /** Models mapped to the UI ModelInfo shape (used by Settings + RightPanel). */
  async getModels(): Promise<ModelInfo[]> {
    const r = await this.listProviderModels();
    return r.ok && r.data.length ? r.data.map(modelFromApi) : mockModels;
  },

  /** Files mapped to the UI FileItem shape (fallback to mocks if down). */
  async getFiles(): Promise<FileItem[]> {
    const r = await this.listFiles();
    return r.ok ? r.data.map(fileItemFromApi) : mockFiles;
  },

  /** Tasks mapped to the UI TaskItem shape. */
  async getTasks(): Promise<TaskItem[]> {
    const r = await this.listTasks();
    return r.ok ? r.data.map(taskItemFromApi) : mockTasks;
  },

  /** Memory mapped to the UI MemoryEntry shape. */
  async getMemory(): Promise<MemoryEntry[]> {
    const r = await this.listMemory({ limit: 100 });
    return r.ok ? r.data.map(memoryEntryFromApi) : mockMemoryEntries;
  },

  /* --- Health ----------------------------------------------------------- */

  /** GET /health (server root). Returns the parsed payload or null when down. */
  async getHealth(): Promise<ApiHealth | null> {
    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), TIMEOUT_MS);
    try {
      const res = await fetch(`${ORIGIN}/health`, { signal: controller.signal });
      if (!res.ok) return null;
      return (await res.json()) as ApiHealth;
    } catch {
      return null;
    } finally {
      clearTimeout(timer);
    }
  },

  /** Boolean liveness check used by the connection store. */
  async health(): Promise<boolean> {
    return (await this.getHealth()) !== null;
  },
};

// Re-export edge mappers for views that fetch raw API types and need to map.
export { fileItemFromApi, memoryEntryFromApi, taskItemFromApi, modelFromApi };

export const apiBaseUrl = BASE;
export const apiOrigin = ORIGIN;

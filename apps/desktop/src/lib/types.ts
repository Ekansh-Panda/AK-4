/**
 * Shared local types for the Miori Core desktop shell.
 * These mirror the eventual FastAPI contracts but stay frontend-owned for v0.1.
 */

/** Miori's live presence — drives the orb + status badge. */
export type PresenceState = "idle" | "listening" | "thinking" | "speaking";

/** Backend / device reachability. */
export type ConnectionStatus = "connected" | "connecting" | "offline";

/** Persona "mood" — how warm vs. focused Miori feels. */
export type PersonaMode = "warm" | "focused" | "playful" | "quiet";

/** Chat roles. */
export type Role = "user" | "miori" | "system";

export interface Attachment {
  id: string;
  name: string;
  size: number;
  kind: "image" | "audio" | "doc" | "other";
}

export interface ChatMessage {
  id: string;
  role: Role;
  content: string;
  createdAt: number;
  /** True while a miori message is still streaming in. */
  streaming?: boolean;
  attachments?: Attachment[];
}

export interface ModelInfo {
  id: string;
  label: string;
  provider: string;
  contextTokens: number;
  local: boolean;
}

export interface ToolInfo {
  id: string;
  name: string;
  active: boolean;
  description: string;
}

export interface MemoryHit {
  id: string;
  snippet: string;
  source: string;
  score: number;
  recalledAt: number;
}

export interface DeviceStatus {
  id: string;
  name: string;
  platform: "windows" | "linux" | "macos" | "web";
  online: boolean;
  lastSeen: number;
  cpu?: number;
  battery?: number;
}

export interface FileItem {
  id: string;
  name: string;
  size: number;
  kind: Attachment["kind"];
  uploadedAt: number;
}

export interface TaskItem {
  id: string;
  title: string;
  done: boolean;
  createdAt: number;
}

export interface MemoryEntry {
  id: string;
  title: string;
  body: string;
  tags: string[];
  pinned: boolean;
  updatedAt: number;
}

/** Right-panel aggregate context, all cleanly typed. */
export interface ContextSnapshot {
  model: ModelInfo;
  tools: ToolInfo[];
  recentMemory: MemoryHit[];
  devices: DeviceStatus[];
  persona: PersonaMode;
}

/* ----------------------------------------------------------------------------
 * Backend wire types — these mirror services/core-api/app/schemas/*.py EXACTLY.
 * They are kept separate from the UI types above so views can map at the edge.
 * ------------------------------------------------------------------------- */

/** services/core-api: MessageOut. role is "user" | "assistant" | "system". */
export interface ApiMessage {
  id: string;
  created_at: string;
  updated_at: string;
  session_id: string;
  role: string;
  content: string;
  model: string | null;
}

/** services/core-api: ChatSessionOut. */
export interface ApiChatSession {
  id: string;
  created_at: string;
  updated_at: string;
  user_id: string | null;
  title: string;
  persona_mode: string;
}

/** services/core-api: ChatResponse (POST /chat). */
export interface ApiChatResponse {
  session_id: string;
  reply: ApiMessage;
}

/** services/core-api: FileOut (list) — lightweight, no extracted_text. */
export interface ApiFile {
  id: string;
  created_at: string;
  updated_at: string;
  user_id: string | null;
  filename: string;
  content_type: string | null;
  size_bytes: number;
  status: string;
  has_text: boolean;
}

/** services/core-api: FileDetail (detail / upload) — adds extracted_text. */
export interface ApiFileDetail extends ApiFile {
  extracted_text: string | null;
}

/** services/core-api: MemoryOut. */
export interface ApiMemory {
  id: string;
  created_at: string;
  updated_at: string;
  user_id: string | null;
  namespace: string;
  content: string;
  meta: string | null;
  pinned: boolean;
}

/** services/core-api: MemoryCreate. */
export interface ApiMemoryCreate {
  content: string;
  namespace?: string;
  user_id?: string | null;
  meta?: string | null;
  pinned?: boolean;
}

/** services/core-api: MemoryUpdate (PATCH). */
export interface ApiMemoryUpdate {
  content?: string | null;
  pinned?: boolean | null;
}

/** services/core-api: TaskOut. status is e.g. "open" | "done". */
export interface ApiTask {
  id: string;
  created_at: string;
  updated_at: string;
  user_id: string | null;
  title: string;
  description: string | null;
  status: string;
  due_at: string | null;
}

/** services/core-api: TaskCreate. */
export interface ApiTaskCreate {
  title: string;
  description?: string | null;
  user_id?: string | null;
  due_at?: string | null;
}

/** services/core-api: TaskUpdate (PATCH). */
export interface ApiTaskUpdate {
  title?: string | null;
  description?: string | null;
  status?: string | null;
  due_at?: string | null;
}

/** services/core-api: PersonaOut. */
export interface ApiPersona {
  name: string;
  tone: string;
  relationship_mode: string;
  verbosity: string;
  humor_level: number;
  operator_mode_style: string;
  voice_profile: string;
  presence_theme: string;
  active_mode: string;
  system_prompt: string;
}

/** services/core-api: ModelInfo. */
export interface ApiModelInfo {
  id: string;
  name: string;
  provider: string;
  context_window: number | null;
}

/** services/core-api: ProviderInfo (GET /providers). */
export interface ApiProviderInfo {
  name: string;
  description: string;
  available: boolean;
  configured: boolean;
  active: boolean;
  models: ApiModelInfo[];
}

/** services/core-api: ProviderStatus (GET /providers/status). */
export interface ApiProviderStatus {
  name: string;
  configured: boolean;
  available: boolean;
  active: boolean;
}

/** services/core-api: SettingOut. */
export interface ApiSetting {
  id: string;
  created_at: string;
  updated_at: string;
  key: string;
  value: string | null;
}

/** services/core-api: DeviceOut (GET /remote/devices). */
export interface ApiDevice {
  id: string;
  created_at: string;
  updated_at: string;
  user_id: string | null;
  name: string;
  platform: string | null;
  state: string;
  is_paired: boolean;
  last_seen_at: string | null;
}

/** services/core-api: RemoteSessionOut. */
export interface ApiRemoteSession {
  id: string;
  device_id: string;
  state: string;
  created_at: string;
}

/** GET /health (server root, not under /api). */
export interface ApiHealth {
  status: string;
  app: string;
  version: string;
  lite_mode: boolean;
  remote_enabled: boolean;
}

/** Discriminated result so callers can distinguish "live" vs "fell back". */
export interface ApiResult<T> {
  data: T;
  /** true when the request hit the backend; false when we served the fallback. */
  ok: boolean;
  /** HTTP status when known (e.g. 413 for oversize uploads). */
  status?: number;
}

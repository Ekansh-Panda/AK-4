/**
 * Shared local types for the Miori Core desktop shell.
 * These mirror the eventual FastAPI contracts but stay frontend-owned for v1.1.0.
 */

/** Miori's live presence — drives the orb + status badge. */
export type PresenceState = "idle" | "listening" | "thinking" | "speaking" | "error";

/**
 * Backend / device reachability.
 * - `degraded`: server is up but a scoped call failed with 401/503
 *   (auth required or a dependency is unavailable).
 */
export type ConnectionStatus =
  | "connected"
  | "connecting"
  | "offline"
  | "degraded";

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
  reachable?: boolean | null;
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

/** services/core-api: ProjectOut (projects router). */
export interface ApiProject {
  id: string;
  created_at: string | null;
  updated_at: string | null;
  name: string;
  description: string | null;
  status: string;
  brief: string | null;
  sessions: { id: string; title: string }[];
  tasks: { id: string; title: string }[];
  files: { id: string; filename: string }[];
}

/** services/core-api: ProjectCreate / ProjectUpdate (projects router). */
export interface ApiProjectCreate {
  name: string;
  description?: string | null;
  brief?: string | null;
  status?: string | null;
  session_ids?: string[];
  task_ids?: string[];
  file_ids?: string[];
}

/** services/core-api: ProjectUpdate (PATCH — all fields optional). */
export type ApiProjectUpdate = Partial<ApiProjectCreate>;
export interface ApiHealth {
  status: string;
  app: string;
  version: string;
  lite_mode: boolean;
  remote_enabled: boolean;
}

/** Discriminated result so callers can distinguish "live" vs "fell back". */
export interface ApiResult<T> {
  /**
   * Parsed body when `ok`, otherwise a neutral empty value (never mock data).
   * Callers must gate real reads on `ok`.
   */
  data: T;
  /** true when the request hit the backend; false on any error / non-2xx. */
  ok: boolean;
  /** HTTP status when known (e.g. 401 auth required, 413 oversize, 503 down). */
  status?: number;
  /** Human-readable failure reason when `ok` is false. */
  error?: string;
  /** true for 401 responses — the backend requires authentication. */
  authRequired?: boolean;
  /** true for 503 responses — the backend is reachable but a dep is down. */
  unavailable?: boolean;
}

/* ----------------------------------------------------------------------------
 * Plans (computer-control execution plans) — mirror app/schemas/plan.py.
 * ------------------------------------------------------------------------- */

/** Lifecycle status for a plan. */
export type PlanStatus =
  | "pending"
  | "running"
  | "completed"
  | "failed"
  | "cancelled"
  | "rejected";

/** Lifecycle status for a single plan step. */
export type PlanStepStatus =
  | "pending"
  | "running"
  | "completed"
  | "failed"
  | "pending_approval"
  | "rejected";

/** services/core-api: PlanOut. */
export interface ApiPlan {
  id: string;
  created_at: string;
  updated_at: string;
  user_id: string;
  device_id: string;
  goal: string;
  trust_level: string;
  status: string;
  parallel: boolean;
  completed_at: string | null;
  error: string | null;
}

/** services/core-api: PlanStepOut. */
export interface ApiPlanStep {
  id: string;
  created_at: string;
  updated_at: string;
  plan_id: string;
  parent_step_id: string | null;
  step_order: number;
  action: string;
  args_json: string | null;
  status: string;
  result: string | null;
  error: string | null;
  retries: number;
  screencap_path: string | null;
  completed_at: string | null;
}

/** services/core-api: PlanDetail (PlanOut + steps). */
export interface ApiPlanDetail extends ApiPlan {
  steps: ApiPlanStep[];
}

/** services/core-api: PlanStepCreate. */
export interface ApiPlanStepCreate {
  action: string;
  args_json?: string | Record<string, unknown> | null;
  parent_step_id?: string | null;
  step_order?: number;
}

/** services/core-api: PlanCreate. */
export interface ApiPlanCreate {
  goal: string;
  parallel?: boolean;
  trust_level?: string;
  steps?: ApiPlanStepCreate[];
}

/** services/core-api: SubPlanCreate. */
export interface ApiSubPlanCreate {
  parent_step_id: string;
  goal: string;
  trust_level?: string;
}

/** services/core-api: ComputerUseSettings (GET/PUT /settings/computer-use). */
export interface ApiComputerUseSettings {
  trust_level: string;
  max_steps: number;
  plan_timeout_s: number;
  vision_enabled: boolean;
  audio_enabled: boolean;
  double_verify: boolean;
  browser_enabled: boolean;
}

/** A single computer-use audit-log row (GET /settings/computer-use/audit). */
export interface ApiComputerUseAudit {
  ts: string | number;
  action: string;
  args?: unknown;
  outcome?: string;
  error?: string | null;
}

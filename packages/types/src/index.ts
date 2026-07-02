/**
 * @miori/types — shared contracts between the Miori Core frontends and core-api.
 *
 * Keep these in sync with services/core-api/app/schemas/*. They intentionally
 * use plain interfaces (no runtime dependency) so any app can import them
 * without bundling cost.
 */

// ---------------------------------------------------------------------------
// Persona
// ---------------------------------------------------------------------------

export type PersonaMode = "friend" | "operator" | "researcher" | "coder";

export interface PersonaConfig {
  name: string;
  tone: string;
  relationshipMode: "friend" | "companion" | "colleague";
  verbosity: "terse" | "balanced" | "expansive";
  humorLevel: "none" | "dry" | "warm" | "playful";
  operatorModeStyle: string;
  voiceProfile: string;
  presenceTheme: string;
  defaultMode: PersonaMode;
  activeMode: PersonaMode;
}

// ---------------------------------------------------------------------------
// Chat
// ---------------------------------------------------------------------------

export type ChatRole = "user" | "assistant" | "system";

export interface ChatMessage {
  id: string;
  sessionId: string;
  role: ChatRole;
  content: string;
  createdAt: string; // ISO 8601
  pending?: boolean;
}

export interface ChatRequest {
  sessionId?: string;
  content: string;
  mode?: PersonaMode;
}

export interface ChatResponse {
  message: ChatMessage;
}

/** Token frames streamed over /ws/chat. */
export interface ChatStreamFrame {
  type: "token" | "done" | "error";
  sessionId: string;
  delta?: string;
  messageId?: string;
  error?: string;
}

// ---------------------------------------------------------------------------
// Memory
// ---------------------------------------------------------------------------

export interface MemoryItem {
  id: string;
  content: string;
  kind: "note" | "fact" | "doc" | "conversation";
  score?: number;
  createdAt: string;
}

export interface MemoryQuery {
  query: string;
  limit?: number;
}

// ---------------------------------------------------------------------------
// Files
// ---------------------------------------------------------------------------

export interface FileItem {
  id: string;
  name: string;
  sizeBytes: number;
  mimeType: string;
  status: "uploaded" | "processing" | "ready" | "error";
  createdAt: string;
}

// ---------------------------------------------------------------------------
// Providers & tools
// ---------------------------------------------------------------------------

export interface ModelInfo {
  id: string;
  provider: string;
  label: string;
  contextWindow?: number;
  available: boolean;
}

export interface ToolInfo {
  name: string;
  description: string;
  enabled: boolean;
}

// ---------------------------------------------------------------------------
// Remote / devices
// ---------------------------------------------------------------------------

export type PowerState = "awake" | "sleeping";

export interface DeviceStatus {
  id: string;
  name: string;
  online: boolean;
  powerState: PowerState;
  cpuPercent?: number;
  memPercent?: number;
  lastSeen: string;
}

export interface RemoteSession {
  id: string;
  deviceId: string;
  connected: boolean;
  createdAt: string;
}

// ---------------------------------------------------------------------------
// Tasks
// ---------------------------------------------------------------------------

export type TaskStatus = "todo" | "in_progress" | "done";

export interface TaskItem {
  id: string;
  title: string;
  notes?: string;
  status: TaskStatus;
  dueAt?: string;
  createdAt: string;
}

// ---------------------------------------------------------------------------
// Settings & presence
// ---------------------------------------------------------------------------

export interface AppSettings {
  theme: "dark" | "system";
  activeModel: string;
  personaMode: PersonaMode;
  remoteEnabled: boolean;
  liteMode: boolean;
}

export type PresenceState = "idle" | "listening" | "thinking" | "speaking" | "offline";

export interface ConnectionStatus {
  apiReachable: boolean;
  wsConnected: boolean;
  presence: PresenceState;
}

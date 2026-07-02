/**
 * Shared types for the Miori remote dashboard.
 *
 * These mirror the shapes the core-api `remote` module is expected to expose.
 * When the real backend lands, keep these aligned with the FastAPI schemas in
 * `services/core-api/app/schemas`.
 */

/** Where the dashboard points and how it authenticates. */
export interface Connection {
  /** Host address incl. scheme + port, e.g. "http://192.168.1.20:8000". */
  host: string;
  /** Bearer / pairing token issued by the host for this device. */
  token: string;
}

export type ConnectionStatus =
  | "disconnected"
  | "connecting"
  | "connected"
  | "error";

/** Result of attempting to connect/pair with a host. */
export interface ConnectResult {
  ok: boolean;
  /** Friendly host name reported back by the machine, if connected. */
  hostName?: string;
  /** Miori core version reported by the host. */
  version?: string;
  /**
   * Whether the host has the remote module enabled (REMOTE_ENABLED=true).
   * Device/power features are only available when this is true. Undefined when
   * we fell back to mock (treated as "available" for the demo).
   */
  remoteEnabled?: boolean;
  /** True when this result came from the offline mock fallback. */
  isMock?: boolean;
  /** Present when ok === false. */
  error?: string;
}

export type ChatRole = "user" | "miori" | "system";

export interface ChatMessage {
  id: string;
  role: ChatRole;
  content: string;
  /** Epoch ms. */
  at: number;
  /** True while a streamed reply is still arriving. */
  streaming?: boolean;
}

/** Snapshot of the host machine's vitals. All values are 0..100 where noted. */
export interface DeviceStatus {
  online: boolean;
  /** CPU load percentage, 0..100. */
  cpu: number;
  /** Memory used percentage, 0..100. */
  mem: number;
  /** Total RAM in GB (for labelling the mem bar). */
  memTotalGb: number;
  /** Seconds since the host process started. */
  uptimeSec: number;
  /** Current assistant power state. */
  power: PowerState;
  /** OS / platform label, e.g. "Linux", "macOS", "Windows". */
  platform: string;
  /** True when these numbers are fabricated (mock fallback or remote disabled). */
  isMock: boolean;
  /**
   * Where this snapshot came from / what the host can do:
   *  - "live"     — real backend with remote enabled, devices present.
   *  - "disabled" — host reachable but REMOTE_ENABLED is false; device/power off.
   *  - "mock"     — offline fallback (host unreachable), fabricated values.
   */
  source: DeviceStatusSource;
  /** Number of registered remote devices (0 when disabled/empty). */
  deviceCount: number;
  /** Number of tasks the host is tracking (best-effort; 0 when unknown). */
  taskCount: number;
  /**
   * The remote device this status/power applies to (first registered device),
   * if any. Needed to target wake/sleep calls.
   */
  deviceId?: string;
  /** Friendly name of the primary device, if any. */
  deviceName?: string;
}

export type DeviceStatusSource = "live" | "disabled" | "mock";

export type PowerState = "awake" | "sleeping";

/** A host-side device as returned by GET /api/remote/devices. */
export interface RemoteDevice {
  id: string;
  name: string;
  platform: string | null;
  /** Raw backend state, e.g. "online" | "sleeping" | "offline". */
  state: string;
  isPaired: boolean;
}

/** A task as returned by GET /api/tasks. */
export interface TaskItem {
  id: string;
  title: string;
  description: string | null;
  status: string;
  dueAt: number | null;
  isMock?: boolean;
}

/** A previously-uploaded file as returned by GET /api/files. */
export interface HostFile {
  id: string;
  filename: string;
  contentType: string | null;
  sizeBytes: number;
  status: string;
}

/** Upload progress callback payload. */
export interface UploadProgress {
  /** 0..100. */
  percent: number;
  loadedBytes: number;
  totalBytes: number;
}

export interface UploadResult {
  ok: boolean;
  fileId?: string;
  name: string;
  sizeBytes: number;
  error?: string;
}

export type ThemeMode = "dark" | "dusk";

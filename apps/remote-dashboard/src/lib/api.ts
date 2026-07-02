/**
 * Typed API client for the Miori host.
 *
 * ┌──────────────────────────────────────────────────────────────────────────┐
 * │ LIVE + MOCK FALLBACK.                                                       │
 * │                                                                            │
 * │ Each method talks to the real core-api when a host is configured AND        │
 * │ reachable; on any fetch/transport failure it falls back to the offline      │
 * │ mock so the demo keeps working with no backend. Whether we're live or       │
 * │ mocked is decided at runtime by a cheap reachability probe done during      │
 * │ `connect()` (see `isLive`); any later transport failure flips back to mock. │
 * │                                                                            │
 * │ Base URL: `import.meta.env.VITE_MIORI_API` (default {host}/api), where      │
 * │ {host} comes from the connection state. Health is server-root (`/health`,   │
 * │ no `/api`). Remote device/power features require the backend to run with    │
 * │ REMOTE_ENABLED=true — when it doesn't, those calls degrade gracefully to a  │
 * │ clear "remote disabled" status instead of crashing.                         │
 * │                                                                            │
 * │ Backend contract (see services/core-api/app/routers/*.py):                  │
 * │   GET  {origin}/health                                                       │
 * │   POST {base}/chat            { message, session_id?, persona_mode? }         │
 * │   POST {base}/files           (multipart, field "file") -> FileDetail         │
 * │   GET  {base}/files           -> FileOut[]                                    │
 * │   GET  {base}/tasks           -> TaskOut[]                                    │
 * │   GET  {base}/remote/devices  -> DeviceOut[]            (REMOTE_ENABLED only) │
 * │   POST {base}/remote/devices/{id}/wake|sleep -> DeviceOut                     │
 * └──────────────────────────────────────────────────────────────────────────┘
 */
import type {
  Connection,
  ConnectResult,
  DeviceStatus,
  HostFile,
  PowerState,
  RemoteDevice,
  TaskItem,
  UploadProgress,
  UploadResult,
} from "./types";
import {
  MOCK_HOST_NAME,
  MOCK_VERSION,
  delay,
  getMockPower,
  makeMockDeviceStatus,
  makeMockFiles,
  makeMockTasks,
  mockReplyFor,
  setMockPower,
} from "./mock";

/* ------------------------------------------------------------------- config */

/**
 * API path prefix. Defaults to "/api" but can be overridden by
 * `VITE_MIORI_API` for setups that mount the API elsewhere (it may be an
 * absolute URL or a bare path). Health lives at the server root, so we derive
 * the origin by stripping a trailing "/api".
 */
const API_PREFIX = (import.meta.env.VITE_MIORI_API ?? "/api").replace(
  /\/+$/,
  "",
);

/** Default request timeout (ms) so an unreachable host fails fast → mock. */
const TIMEOUT_MS = 6000;

/**
 * Runtime live/mock decision. Set true by `connect()` once the host's /health
 * responds; reset to false on any later transport failure. Defaults to false so
 * the app is usable via the mock before the first successful probe.
 */
let _live = false;

/** Persisted chat session id, so multi-turn context survives across sends. */
let _sessionId: string | null = null;

/** Whether the host reported the remote module as enabled. */
let _remoteEnabled = false;

export function isLive(): boolean {
  return _live;
}

export function remoteEnabled(): boolean {
  return _remoteEnabled;
}

export function resetSession(): void {
  _sessionId = null;
}

/* --------------------------------------------------------------- url helpers */

/** Origin of the host (scheme + authority), trailing slashes stripped. */
function origin(conn: Connection): string {
  return conn.host.trim().replace(/\/+$/, "");
}

/** Build a URL against the API base ({host}{API_PREFIX}{path}). */
function apiUrl(conn: Connection, path: string): string {
  // If VITE_MIORI_API is an absolute URL, honour it verbatim as the base.
  if (/^https?:\/\//i.test(API_PREFIX)) {
    return `${API_PREFIX}${path}`;
  }
  return `${origin(conn)}${API_PREFIX}${path}`;
}

/** Build a URL against the server root ({host}{path}) — used for /health. */
function rootUrl(conn: Connection, path: string): string {
  return `${origin(conn)}${path}`;
}

/** Standard auth headers for the host's bearer/pairing token. */
function authHeaders(conn: Connection): HeadersInit {
  const h: Record<string, string> = { "X-Miori-Remote": "1" };
  if (conn.token.trim()) h.Authorization = `Bearer ${conn.token.trim()}`;
  return h;
}

/** fetch with a timeout + the caller's abort signal, so we fail fast → mock. */
async function timedFetch(
  input: string,
  init: RequestInit = {},
  signal?: AbortSignal,
): Promise<Response> {
  const ctrl = new AbortController();
  const timer = setTimeout(() => ctrl.abort(), TIMEOUT_MS);
  // Chain the caller's signal into our controller.
  if (signal) {
    if (signal.aborted) ctrl.abort();
    else signal.addEventListener("abort", () => ctrl.abort(), { once: true });
  }
  try {
    return await fetch(input, { ...init, signal: ctrl.signal });
  } finally {
    clearTimeout(timer);
  }
}

/* ------------------------------------------------------------------ connect */

/**
 * Connect / pair with a host.
 *
 * Probes `GET {host}/health` (server root) to confirm reachability and read the
 * version + remote flag. A reachable host flips us into LIVE mode; an
 * unreachable host (or empty fields) cleanly falls back to the mock so the demo
 * still works offline.
 */
export async function connect(conn: Connection): Promise<ConnectResult> {
  if (!conn.host.trim()) {
    return { ok: false, error: "Enter the host address." };
  }

  try {
    const res = await timedFetch(rootUrl(conn, "/health"), {
      headers: authHeaders(conn),
    });
    if (!res.ok) {
      // Host is reachable but unhappy (e.g. 401/403). Surface it; stay mock.
      _live = false;
      return { ok: false, error: `Host responded ${res.status}.` };
    }
    const data = (await res.json()) as {
      app?: string;
      version?: string;
      remote_enabled?: boolean;
    };
    _live = true;
    _remoteEnabled = Boolean(data.remote_enabled);
    return {
      ok: true,
      hostName: data.app ?? "Miori host",
      version: data.version,
      remoteEnabled: _remoteEnabled,
      isMock: false,
    };
  } catch {
    // Unreachable host → graceful offline mock so the dashboard stays usable.
    _live = false;
    _remoteEnabled = true; // mock pretends remote is available
    await delay(500, 300);
    return {
      ok: true,
      hostName: MOCK_HOST_NAME,
      version: MOCK_VERSION,
      remoteEnabled: true,
      isMock: true,
    };
  }
}

/* --------------------------------------------------------------- sendMessage */

/**
 * Send a chat message and surface Miori's reply.
 *
 * Real path: `POST {base}/chat` with a persisted `session_id` (REST, no
 * streaming — fine for mobile). The full reply text is delivered to `onChunk`
 * in word-sized pieces so the existing typed-reply UI still animates. Mock path
 * is the offline fallback.
 *
 * Returns the full reply text. Honours `signal` for cancellation.
 */
export async function sendMessage(
  conn: Connection,
  text: string,
  onChunk: (delta: string) => void,
  signal?: AbortSignal,
): Promise<string> {
  if (_live) {
    try {
      const res = await timedFetch(
        apiUrl(conn, "/chat"),
        {
          method: "POST",
          headers: {
            ...authHeaders(conn),
            "Content-Type": "application/json",
          },
          body: JSON.stringify({
            message: text,
            session_id: _sessionId ?? undefined,
          }),
        },
        signal,
      );
      if (!res.ok) throw new Error(`chat failed (${res.status})`);
      const data = (await res.json()) as {
        session_id: string;
        reply: { content: string };
      };
      _sessionId = data.session_id;
      // Replay the reply as word chunks so the typed-reply UI keeps its rhythm.
      await emitTyped(data.reply.content ?? "", onChunk, signal);
      return data.reply.content ?? "";
    } catch (err) {
      // Mid-conversation failure: if the call was deliberately aborted, rethrow
      // so the caller can leave the partial reply; otherwise fall back to mock.
      if (signal?.aborted) throw err;
      _live = false;
    }
  }

  // --- offline mock fallback ---
  const reply = mockReplyFor(text);
  await emitTyped(reply, onChunk, signal, true);
  return reply;
}

/** Emit text to `onChunk` word-by-word for the typed-reply animation. */
async function emitTyped(
  full: string,
  onChunk: (delta: string) => void,
  signal?: AbortSignal,
  pause = false,
): Promise<void> {
  if (pause) await delay(380, 220); // mock "thinking" beat
  const words = full.split(" ");
  let first = true;
  for (const word of words) {
    if (signal?.aborted) break;
    onChunk((first ? "" : " ") + word);
    first = false;
    await delay(pause ? 38 : 14, pause ? 60 : 26);
  }
}

/* ----------------------------------------------------------- getDeviceStatus */

/**
 * Fetch a host status snapshot.
 *
 * The backend has no single `/remote/status` endpoint, so we synthesise one:
 *  - `GET {origin}/health` for online/uptime-ish + platform-ish meta, and
 *  - `GET {base}/remote/devices` for the primary device's power state.
 * If REMOTE_ENABLED is false the devices route 404s — we return a clear
 * `source: "disabled"` status instead of crashing. Unreachable → mock.
 */
export async function getDeviceStatus(conn: Connection): Promise<DeviceStatus> {
  if (_live) {
    try {
      // Confirm the host is alive (cheap, always present).
      const healthRes = await timedFetch(rootUrl(conn, "/health"), {
        headers: authHeaders(conn),
      });
      if (!healthRes.ok) throw new Error(`health ${healthRes.status}`);
      const health = (await healthRes.json()) as {
        remote_enabled?: boolean;
      };
      _remoteEnabled = Boolean(health.remote_enabled);

      // Best-effort task count (independent of remote).
      const taskCount = await safeTaskCount(conn);

      if (!_remoteEnabled) {
        return remoteDisabledStatus(taskCount);
      }

      const devices = await listDevices(conn);
      const primary = devices[0];
      const power: PowerState =
        primary && primary.state === "sleeping" ? "sleeping" : "awake";
      return {
        online: true,
        // No real CPU/mem metric exists yet; show neutral live placeholders
        // rather than fabricated drift so it's honestly "live but unmetered".
        cpu: 0,
        mem: 0,
        memTotalGb: 0,
        uptimeSec: 0,
        power,
        platform: primary?.platform ?? "Host",
        isMock: false,
        source: "live",
        deviceCount: devices.length,
        taskCount,
        deviceId: primary?.id,
        deviceName: primary?.name,
      };
    } catch {
      _live = false;
    }
  }

  // --- offline mock fallback ---
  await delay(250, 200);
  return makeMockDeviceStatus();
}

/** A clear "remote disabled" status — host is up but device control is off. */
function remoteDisabledStatus(taskCount: number): DeviceStatus {
  return {
    online: true,
    cpu: 0,
    mem: 0,
    memTotalGb: 0,
    uptimeSec: 0,
    power: "awake",
    platform: "Host",
    isMock: false,
    source: "disabled",
    deviceCount: 0,
    taskCount,
  };
}

/** GET {base}/remote/devices → RemoteDevice[]. Empty on 404 (remote off). */
async function listDevices(conn: Connection): Promise<RemoteDevice[]> {
  const res = await timedFetch(apiUrl(conn, "/remote/devices"), {
    headers: authHeaders(conn),
  });
  if (res.status === 404) return [];
  if (!res.ok) throw new Error(`devices ${res.status}`);
  const rows = (await res.json()) as Array<{
    id: string;
    name: string;
    platform: string | null;
    state: string;
    is_paired: boolean;
  }>;
  return rows.map((d) => ({
    id: d.id,
    name: d.name,
    platform: d.platform,
    state: d.state,
    isPaired: d.is_paired,
  }));
}

/** Best-effort task count; never throws (0 on any failure). */
async function safeTaskCount(conn: Connection): Promise<number> {
  try {
    const tasks = await getTasks(conn);
    return tasks.length;
  } catch {
    return 0;
  }
}

/* -------------------------------------------------------------- setPowerState */

/**
 * Wake or sleep the host's primary device.
 *
 * Real path: `POST {base}/remote/devices/{id}/wake|sleep`. Requires both
 * REMOTE_ENABLED and a registered device id (caller passes it from the device
 * status). Without an id we register a device on the fly so the demo flow is
 * never a dead end. Unreachable / remote-off → mock toggle.
 */
export async function setPowerState(
  conn: Connection,
  state: PowerState,
  deviceId?: string,
): Promise<PowerState> {
  if (_live && _remoteEnabled) {
    try {
      const id = deviceId ?? (await ensureDevice(conn));
      if (id) {
        const verb = state === "awake" ? "wake" : "sleep";
        const res = await timedFetch(
          apiUrl(conn, `/remote/devices/${id}/${verb}`),
          { method: "POST", headers: authHeaders(conn) },
        );
        if (!res.ok) throw new Error(`power ${res.status}`);
        const dev = (await res.json()) as { state: string };
        return dev.state === "sleeping" ? "sleeping" : "awake";
      }
    } catch {
      _live = false;
    }
  }

  // --- offline mock fallback ---
  await delay(900, 400);
  return setMockPower(state);
}

/**
 * Ensure at least one device exists to target (registers "this phone" if the
 * host has none yet). Returns the device id, or null on failure.
 */
async function ensureDevice(conn: Connection): Promise<string | null> {
  try {
    const existing = await listDevices(conn);
    if (existing[0]) return existing[0].id;
    const res = await timedFetch(apiUrl(conn, "/remote/devices"), {
      method: "POST",
      headers: { ...authHeaders(conn), "Content-Type": "application/json" },
      body: JSON.stringify({ name: "Phone (remote dashboard)", platform: "web" }),
    });
    if (!res.ok) return null;
    const dev = (await res.json()) as { id: string };
    return dev.id;
  } catch {
    return null;
  }
}

/** Read the current mocked power state without hitting the network. */
export function currentPowerState(): PowerState {
  return getMockPower();
}

/* -------------------------------------------------------------------- tasks */

/** GET {base}/tasks → TaskItem[]. Falls back to canned tasks offline. */
export async function getTasks(conn: Connection): Promise<TaskItem[]> {
  if (_live) {
    try {
      const res = await timedFetch(apiUrl(conn, "/tasks"), {
        headers: authHeaders(conn),
      });
      if (!res.ok) throw new Error(`tasks ${res.status}`);
      const rows = (await res.json()) as Array<{
        id: string;
        title: string;
        description: string | null;
        status: string;
        due_at: string | null;
      }>;
      return rows.map((t) => ({
        id: t.id,
        title: t.title,
        description: t.description,
        status: t.status,
        dueAt: t.due_at ? Date.parse(t.due_at) : null,
      }));
    } catch {
      _live = false;
    }
  }
  await delay(220, 160);
  return makeMockTasks();
}

/* -------------------------------------------------------------------- files */

/** GET {base}/files → HostFile[]. Falls back to canned files offline. */
export async function getFiles(conn: Connection): Promise<HostFile[]> {
  if (_live) {
    try {
      const res = await timedFetch(apiUrl(conn, "/files"), {
        headers: authHeaders(conn),
      });
      if (!res.ok) throw new Error(`files ${res.status}`);
      const rows = (await res.json()) as Array<{
        id: string;
        filename: string;
        content_type: string | null;
        size_bytes: number;
        status: string;
      }>;
      return rows.map((f) => ({
        id: f.id,
        filename: f.filename,
        contentType: f.content_type,
        sizeBytes: f.size_bytes,
        status: f.status,
      }));
    } catch {
      _live = false;
    }
  }
  await delay(200, 150);
  return makeMockFiles();
}

/* ----------------------------------------------------------------- uploadFile */

/**
 * Upload a file from the phone to the host.
 *
 * Real path: `POST {base}/files` (multipart, field "file") via XMLHttpRequest
 * for real upload progress → `onProgress`. On transport error we drop to the
 * mock animation so the UI still completes. Honours `signal` for cancellation.
 */
export function uploadFile(
  conn: Connection,
  file: File,
  onProgress: (p: UploadProgress) => void,
  signal?: AbortSignal,
): Promise<UploadResult> {
  if (_live) {
    return new Promise<UploadResult>((resolve) => {
      const form = new FormData();
      form.append("file", file);
      const xhr = new XMLHttpRequest();
      xhr.open("POST", apiUrl(conn, "/files"));
      if (conn.token.trim()) {
        xhr.setRequestHeader("Authorization", `Bearer ${conn.token.trim()}`);
      }
      xhr.setRequestHeader("X-Miori-Remote", "1");

      xhr.upload.onprogress = (e) => {
        if (!e.lengthComputable) return;
        onProgress({
          percent: Math.round((e.loaded / e.total) * 100),
          loadedBytes: e.loaded,
          totalBytes: e.total,
        });
      };
      xhr.onload = () => {
        if (xhr.status >= 200 && xhr.status < 300) {
          let fileId: string | undefined;
          try {
            fileId = (JSON.parse(xhr.responseText) as { id?: string }).id;
          } catch {
            /* non-JSON body — leave id undefined */
          }
          onProgress({ percent: 100, loadedBytes: file.size, totalBytes: file.size });
          resolve({ ok: true, fileId, name: file.name, sizeBytes: file.size });
        } else {
          // Surface a clear server error rather than silently mocking.
          resolve({
            ok: false,
            name: file.name,
            sizeBytes: file.size,
            error: `Host rejected upload (${xhr.status}).`,
          });
        }
      };
      xhr.onerror = () => {
        // Transport failure → mark offline and run the mock so the UI completes.
        _live = false;
        void mockUpload(file, onProgress, signal).then(resolve);
      };
      if (signal) {
        if (signal.aborted) xhr.abort();
        else signal.addEventListener("abort", () => xhr.abort(), { once: true });
      }
      xhr.onabort = () =>
        resolve({
          ok: false,
          name: file.name,
          sizeBytes: file.size,
          error: "Cancelled.",
        });
      xhr.send(form);
    });
  }

  // --- offline mock fallback ---
  return mockUpload(file, onProgress, signal);
}

/** Animated mock upload to 100% (offline fallback). */
async function mockUpload(
  file: File,
  onProgress: (p: UploadProgress) => void,
  signal?: AbortSignal,
): Promise<UploadResult> {
  const total = file.size || 1;
  const steps = 24;
  for (let i = 1; i <= steps; i++) {
    if (signal?.aborted) {
      return { ok: false, name: file.name, sizeBytes: file.size, error: "Cancelled." };
    }
    const percent = Math.round((i / steps) * 100);
    onProgress({
      percent,
      loadedBytes: Math.round((percent / 100) * total),
      totalBytes: total,
    });
    await delay(70, 90);
  }
  return {
    ok: true,
    fileId: `mock_${Date.now().toString(36)}`,
    name: file.name,
    sizeBytes: file.size,
  };
}

/**
 * Mock data + helpers for the remote dashboard.
 *
 * Everything here is fabricated so the UI is fully explorable before the
 * core-api `remote` module exists. Each consumer should make it visually clear
 * to the user that the data is mocked (see `DeviceStatus.isMock`, "mock" chips).
 *
 * TODO(remote-backend): delete this file once `src/lib/api.ts` talks to the real
 *   endpoints (/api/remote, /ws/remote, /api/chat).
 */
import type { DeviceStatus, HostFile, PowerState, TaskItem } from "./types";

export const MOCK_HOST_NAME = "miori-host";
export const MOCK_VERSION = "0.1.0";

/** Resolve after `ms`, optionally jittered, so mocks feel like real latency. */
export function delay(ms: number, jitter = 0): Promise<void> {
  const wait = ms + (jitter ? Math.random() * jitter : 0);
  return new Promise((resolve) => setTimeout(resolve, wait));
}

let _power: PowerState = "awake";

export function getMockPower(): PowerState {
  return _power;
}

export function setMockPower(next: PowerState): PowerState {
  _power = next;
  return _power;
}

/**
 * Produce a believable, gently-drifting device snapshot. Values wander around a
 * baseline so the dashboard's bars move a little on each poll.
 */
export function makeMockDeviceStatus(): DeviceStatus {
  const drift = (base: number, spread: number) =>
    Math.max(0, Math.min(100, Math.round(base + (Math.random() - 0.5) * spread)));

  const awake = _power === "awake";
  return {
    online: true,
    // When sleeping, the host idles low.
    cpu: awake ? drift(28, 22) : drift(6, 6),
    mem: awake ? drift(54, 12) : drift(38, 8),
    memTotalGb: 16,
    uptimeSec: 60 * 60 * 7 + Math.floor(Math.random() * 600),
    power: _power,
    platform: "Linux",
    isMock: true,
    source: "mock",
    deviceCount: 1,
    taskCount: MOCK_TASKS.length,
    deviceId: "mock-device",
    deviceName: MOCK_HOST_NAME,
  };
}

/** Canned tasks for the offline fallback. */
export const MOCK_TASKS: TaskItem[] = [
  {
    id: "mock-task-1",
    title: "Summarise the dropped notes",
    description: "Pull the key points out of today's uploads.",
    status: "in_progress",
    dueAt: null,
    isMock: true,
  },
  {
    id: "mock-task-2",
    title: "Watch the host's disk space",
    description: null,
    status: "pending",
    dueAt: null,
    isMock: true,
  },
  {
    id: "mock-task-3",
    title: "Nightly memory digest",
    description: "Roll up the day's conversations.",
    status: "done",
    dueAt: null,
    isMock: true,
  },
];

export function makeMockTasks(): TaskItem[] {
  return MOCK_TASKS.map((t) => ({ ...t }));
}

/** Canned uploaded-file listing for the offline fallback. */
export function makeMockFiles(): HostFile[] {
  return [
    {
      id: "mock-file-1",
      filename: "meeting-notes.pdf",
      contentType: "application/pdf",
      sizeBytes: 184_320,
      status: "ready",
    },
    {
      id: "mock-file-2",
      filename: "diagram.png",
      contentType: "image/png",
      sizeBytes: 52_104,
      status: "ready",
    },
  ];
}

/**
 * A canned Miori reply, chosen loosely from the user's text so the mock chat
 * feels responsive rather than random. Warm, friend-like, never servile —
 * matching the Miori persona.
 */
export function mockReplyFor(userText: string): string {
  const t = userText.toLowerCase();
  if (/\b(hi|hey|hello|yo)\b/.test(t)) {
    return "Hey — I'm right here. The host's awake and listening. What's on your mind?";
  }
  if (t.includes("status") || t.includes("cpu") || t.includes("memory")) {
    return "The machine's breathing easy right now — load's low and there's plenty of headroom. Want the full readout? Tap over to Device.";
  }
  if (t.includes("sleep")) {
    return "I can wind the host down whenever you like — just hit Sleep on the Power tab and I'll go quiet until you call.";
  }
  if (t.includes("file") || t.includes("upload")) {
    return "Send it over from the Files tab and I'll catch it on the host side. I'll let you know once it lands.";
  }
  if (t.includes("thank")) {
    return "Anytime. That's the whole point of me.";
  }
  return "Got it. I'm running this one on the host and I'll keep you posted — this reply's mocked for now, but the wiring's all here.";
}

/** Opening line shown when the chat first loads. */
export const MOCK_GREETING =
  "Hey, you reached me from your phone. I'm watching over the host — ask me anything or steer it from the tabs below.";

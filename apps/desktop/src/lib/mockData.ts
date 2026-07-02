import type {
  ChatMessage,
  ContextSnapshot,
  DeviceStatus,
  FileItem,
  MemoryEntry,
  MemoryHit,
  ModelInfo,
  TaskItem,
  ToolInfo,
} from "./types";

/** Stable-ish id helper for mock + optimistic local state. */
export function uid(prefix = "id"): string {
  return `${prefix}_${Math.random().toString(36).slice(2, 10)}`;
}

const now = Date.now();

export const mockModels: ModelInfo[] = [
  {
    id: "local-mistral-7b",
    label: "Mistral 7B (local)",
    provider: "llama.cpp",
    contextTokens: 8192,
    local: true,
  },
  {
    id: "claude-sonnet",
    label: "Claude Sonnet",
    provider: "Anthropic",
    contextTokens: 200000,
    local: false,
  },
  {
    id: "gpt-4o-mini",
    label: "GPT-4o mini",
    provider: "OpenAI",
    contextTokens: 128000,
    local: false,
  },
];

export const mockTools: ToolInfo[] = [
  { id: "memory", name: "Memory recall", active: true, description: "Long-term recall over your notes." },
  { id: "files", name: "File reader", active: true, description: "Reads attached documents." },
  { id: "web", name: "Web research", active: false, description: "Fetches and summarizes pages." },
  { id: "shell", name: "Local shell", active: false, description: "Runs sandboxed commands." },
];

export const mockMemoryHits: MemoryHit[] = [
  {
    id: uid("mem"),
    snippet: "You prefer terse morning summaries, no fluff.",
    source: "preferences",
    score: 0.92,
    recalledAt: now - 1000 * 60 * 4,
  },
  {
    id: uid("mem"),
    snippet: "Project 'Aurora' deadline is the 30th.",
    source: "projects/aurora",
    score: 0.81,
    recalledAt: now - 1000 * 60 * 12,
  },
  {
    id: uid("mem"),
    snippet: "You're learning Rust on weekends.",
    source: "journal",
    score: 0.74,
    recalledAt: now - 1000 * 60 * 30,
  },
];

export const mockDevices: DeviceStatus[] = [
  {
    id: "dev-desktop",
    name: "Studio Desktop",
    platform: "linux",
    online: true,
    lastSeen: now,
    cpu: 18,
  },
  {
    id: "dev-laptop",
    name: "Travel Laptop",
    platform: "macos",
    online: false,
    lastSeen: now - 1000 * 60 * 60 * 5,
    battery: 64,
  },
  {
    id: "dev-phone",
    name: "Phone (remote)",
    platform: "web",
    online: true,
    lastSeen: now - 1000 * 30,
    battery: 88,
  },
];

export const mockMessages: ChatMessage[] = [
  {
    id: uid("msg"),
    role: "miori",
    content: "Hey. I'm here whenever you want to start — no rush.",
    createdAt: now - 1000 * 60 * 2,
  },
];

export const mockFiles: FileItem[] = [
  { id: uid("file"), name: "aurora-spec.pdf", size: 482_000, kind: "doc", uploadedAt: now - 1000 * 60 * 90 },
  { id: uid("file"), name: "voice-note.m4a", size: 1_204_000, kind: "audio", uploadedAt: now - 1000 * 60 * 200 },
  { id: uid("file"), name: "moodboard.png", size: 920_000, kind: "image", uploadedAt: now - 1000 * 60 * 320 },
];

export const mockTasks: TaskItem[] = [
  { id: uid("task"), title: "Sketch the Miori orb states", done: true, createdAt: now - 1000 * 60 * 400 },
  { id: uid("task"), title: "Draft Aurora project brief", done: false, createdAt: now - 1000 * 60 * 200 },
  { id: uid("task"), title: "Reply to Sam about the demo", done: false, createdAt: now - 1000 * 60 * 60 },
];

export const mockMemoryEntries: MemoryEntry[] = [
  {
    id: uid("entry"),
    title: "Communication style",
    body: "Likes terse, warm, direct replies. Hates corporate filler.",
    tags: ["preferences", "tone"],
    pinned: true,
    updatedAt: now - 1000 * 60 * 60 * 24,
  },
  {
    id: uid("entry"),
    title: "Project Aurora",
    body: "Personal venture. Deadline the 30th. Stack TBD.",
    tags: ["projects"],
    pinned: false,
    updatedAt: now - 1000 * 60 * 60 * 6,
  },
];

export const mockContext: ContextSnapshot = {
  model: mockModels[0],
  tools: mockTools,
  recentMemory: mockMemoryHits,
  devices: mockDevices,
  persona: "warm",
};

/** Canned streaming reply used by the mock websocket. */
export const mockReply =
  "Got it. Here's how I'd think about that: start small, keep the moving parts few, " +
  "and let it grow only where it earns its place. Want me to sketch the first step?";

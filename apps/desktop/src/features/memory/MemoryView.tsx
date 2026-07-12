import { useCallback, useEffect, useState, type FormEvent } from "react";
import { Pin, Trash2, Plus, Check, X, Pencil } from "lucide-react";
import { PageContainer } from "@/components/layout/PageContainer";
import { Input, Textarea } from "@/components/ui/Input";
import { Button } from "@/components/ui/Button";
import { api, memoryEntryFromApi } from "@/lib/api";
import { cn } from "@/lib/cn";
import type { ApiMemory } from "@/lib/types";

export function MemoryView() {
  const [items, setItems] = useState<ApiMemory[]>([]);
  const [offline, setOffline] = useState(false);
  const [query, setQuery] = useState("");
  const [pinnedOnly, setPinnedOnly] = useState(false);
  const [kind, setKind] = useState<string>("");
  const [draft, setDraft] = useState("");
  const [adding, setAdding] = useState(false);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [editText, setEditText] = useState("");

  const load = useCallback(async () => {
    const r = await api.listMemory({
      kind: kind || undefined,
      pinned: pinnedOnly ? true : undefined,
      limit: 200,
    });
    setOffline(!r.ok);
    if (r.ok) {
      setItems(r.data);
    } else {
      // Backend unreachable — show an honest empty state (no mock data).
      setItems([]);
    }
  }, [kind, pinnedOnly]);

  useEffect(() => {
    void load();
  }, [load]);

  const add = async (e: FormEvent) => {
    e.preventDefault();
    const content = draft.trim();
    if (!content) return;
    setAdding(true);
    try {
      const r = await api.createMemory({
        content,
        namespace: kind || "user:facts",
      });
      if (r.ok) {
        setDraft("");
        await load();
      }
    } finally {
      setAdding(false);
    }
  };

  const togglePin = async (m: ApiMemory) => {
    // Optimistic flip, then PATCH.
    setItems((prev) =>
      prev.map((x) => (x.id === m.id ? { ...x, pinned: !x.pinned } : x)),
    );
    await api.updateMemory(m.id, { pinned: !m.pinned });
    void load();
  };

  const remove = async (id: string) => {
    setItems((prev) => prev.filter((x) => x.id !== id));
    await api.deleteMemory(id);
  };

  const startEdit = (m: ApiMemory) => {
    setEditingId(m.id);
    setEditText(m.content);
  };

  const saveEdit = async (id: string) => {
    const content = editText.trim();
    setEditingId(null);
    if (!content) return;
    await api.updateMemory(id, { content });
    void load();
  };

  const q = query.trim().toLowerCase();
  const filtered = items.filter((m) => !q || m.content.toLowerCase().includes(q));
  const sorted = [...filtered].sort(
    (a, b) =>
      Number(b.pinned) - Number(a.pinned) ||
      (Date.parse(b.updated_at) || 0) - (Date.parse(a.updated_at) || 0),
  );

  return (
    <PageContainer title="Memory" subtitle="What Miori remembers about you — and why.">
      {/* Create */}
      <form onSubmit={add} className="mb-4 flex gap-2">
        <Input
          value={draft}
          onChange={(e) => setDraft(e.target.value)}
          placeholder="Remember something new…"
        />
        <Button type="submit" variant="primary" size="icon" aria-label="Add memory" disabled={adding}>
          <Plus size={18} />
        </Button>
      </form>

      {/* Filters */}
      <div className="mb-6 flex flex-wrap items-center gap-2">
        <Input
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="Search memory…"
          className="flex-1 min-w-[12rem]"
        />
        <Input
          value={kind}
          onChange={(e) => setKind(e.target.value)}
          placeholder="kind / namespace"
          className="w-44"
        />
        <Button
          variant={pinnedOnly ? "primary" : "subtle"}
          size="sm"
          onClick={() => setPinnedOnly((v) => !v)}
        >
          <Pin size={13} className={cn(pinnedOnly && "fill-current")} /> Pinned
        </Button>
      </div>

      {offline && (
        <p className="mb-4 text-xs text-ink-faint">
          Backend unreachable — connect the server to load and edit memory.
        </p>
      )}

      <div className="grid gap-3 sm:grid-cols-2">
        {sorted.map((m) => {
          const entry = memoryEntryFromApi(m);
          const editing = editingId === m.id;
          return (
            <article key={m.id} className="glass-soft rounded p-4">
              <div className="mb-1 flex items-start justify-between gap-2">
                <h3 className="text-sm font-medium text-ink">{entry.title}</h3>
                <div className="flex shrink-0 items-center gap-2">
                  <button
                    onClick={() => (editing ? setEditingId(null) : startEdit(m))}
                    aria-label="Edit"
                    className="text-ink-faint transition-colors hover:text-ink-soft"
                  >
                    <Pencil size={13} />
                  </button>
                  <button
                    onClick={() => void togglePin(m)}
                    aria-label={m.pinned ? "Unpin" : "Pin"}
                    className={cn(
                      "transition-colors",
                      m.pinned ? "text-accent" : "text-ink-faint hover:text-ink-soft",
                    )}
                  >
                    <Pin size={14} className={cn(m.pinned && "fill-current")} />
                  </button>
                  <button
                    onClick={() => void remove(m.id)}
                    aria-label="Delete"
                    className="text-ink-faint transition-colors hover:text-danger"
                  >
                    <Trash2 size={14} />
                  </button>
                </div>
              </div>

              {editing ? (
                <div className="space-y-2">
                  <Textarea
                    rows={4}
                    value={editText}
                    onChange={(e) => setEditText(e.target.value)}
                  />
                  <div className="flex gap-2">
                    <Button variant="primary" size="sm" onClick={() => void saveEdit(m.id)}>
                      <Check size={13} /> Save
                    </Button>
                    <Button variant="subtle" size="sm" onClick={() => setEditingId(null)}>
                      <X size={13} /> Cancel
                    </Button>
                  </div>
                </div>
              ) : (
                <>
                  <p className="text-sm leading-relaxed text-ink-soft">{entry.body}</p>
                  {entry.tags.length > 0 && (
                    <div className="mt-3 flex flex-wrap gap-1.5">
                      {entry.tags.map((t) => (
                        <span
                          key={t}
                          className="rounded-full bg-white/[0.05] px-2 py-0.5 text-[0.65rem] text-ink-faint"
                        >
                          {t}
                        </span>
                      ))}
                    </div>
                  )}
                </>
              )}
            </article>
          );
        })}
        {sorted.length === 0 && (
          <p className="text-sm text-ink-faint">No matching memories.</p>
        )}
      </div>
    </PageContainer>
  );
}

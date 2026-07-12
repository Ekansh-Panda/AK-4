import { useCallback, useEffect, useState, type FormEvent } from "react";
import { Plus, Check, Trash2 } from "lucide-react";
import { PageContainer } from "@/components/layout/PageContainer";
import { Input } from "@/components/ui/Input";
import { Button } from "@/components/ui/Button";
import { api } from "@/lib/api";
import { cn } from "@/lib/cn";
import type { ApiTask } from "@/lib/types";

function isDone(t: ApiTask): boolean {
  return t.status === "done" || t.status === "completed";
}

export function TasksView() {
  const [tasks, setTasks] = useState<ApiTask[]>([]);
  const [offline, setOffline] = useState(false);
  const [draft, setDraft] = useState("");
  const [busy, setBusy] = useState(false);

  const load = useCallback(async () => {
    const r = await api.listTasks();
    setOffline(!r.ok);
    if (r.ok) {
      setTasks(r.data);
    } else {
      // Backend unreachable — show an honest empty state (no mock data).
      setTasks([]);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  const add = async (e: FormEvent) => {
    e.preventDefault();
    const title = draft.trim();
    if (!title) return;
    setBusy(true);
    try {
      const r = await api.createTask({ title });
      if (r.ok) {
        setDraft("");
        await load();
      }
    } finally {
      setBusy(false);
    }
  };

  const toggle = async (t: ApiTask) => {
    const next = isDone(t) ? "pending" : "done";
    setTasks((prev) => prev.map((x) => (x.id === t.id ? { ...x, status: next } : x)));
    await api.updateTask(t.id, { status: next });
    void load();
  };

  const remove = async (id: string) => {
    setTasks((prev) => prev.filter((x) => x.id !== id));
    await api.deleteTask(id);
  };

  const open = tasks.filter((t) => !isDone(t));
  const done = tasks.filter((t) => isDone(t));

  return (
    <PageContainer title="Tasks" subtitle="Small things Miori is helping you track.">
      <form onSubmit={add} className="mb-6 flex gap-2">
        <Input
          value={draft}
          onChange={(e) => setDraft(e.target.value)}
          placeholder="Add a task…"
        />
        <Button type="submit" variant="primary" size="icon" aria-label="Add task" disabled={busy}>
          <Plus size={18} />
        </Button>
      </form>

      {offline && (
        <p className="mb-4 text-xs text-ink-faint">
          Backend unreachable — connect the server to load and manage tasks.
        </p>
      )}

      <ul className="space-y-2">
        {[...open, ...done].map((t) => {
          const done = isDone(t);
          return (
            <li
              key={t.id}
              className="glass-soft flex items-center gap-3 rounded px-4 py-3"
            >
              <button
                onClick={() => void toggle(t)}
                aria-label={done ? "Mark not done" : "Mark done"}
                className={cn(
                  "grid h-5 w-5 place-items-center rounded-sm border transition-colors",
                  done
                    ? "border-accent bg-accent/80 text-canvas"
                    : "border-white/20 hover:border-accent/60",
                )}
              >
                {done && <Check size={13} />}
              </button>
              <span
                className={cn(
                  "flex-1 text-sm",
                  done ? "text-ink-faint line-through" : "text-ink",
                )}
              >
                {t.title}
              </span>
              <button
                onClick={() => void remove(t.id)}
                aria-label="Delete task"
                className="text-ink-faint transition-colors hover:text-danger"
              >
                <Trash2 size={15} />
              </button>
            </li>
          );
        })}
        {tasks.length === 0 && <li className="text-sm text-ink-faint">Nothing yet.</li>}
      </ul>
    </PageContainer>
  );
}

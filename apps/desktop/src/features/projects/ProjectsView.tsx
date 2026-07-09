import { useEffect, useState, useCallback } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Plus, Trash2, Archive, FolderOpen, FileText, Pencil } from "lucide-react";
import { PageContainer } from "@/components/layout/PageContainer";
import { Button } from "@/components/ui/Button";
import { Card, CardHeader, CardTitle, CardBody } from "@/components/ui/Card";
import { Input, Textarea } from "@/components/ui/Input";
import { StatusBadge } from "@/components/ui/StatusBadge";
import { api } from "@/lib/api";

interface Project {
  id: string;
  name: string;
  description: string | null;
  status: string;
  brief: string | null;
  created_at: string | null;
  updated_at: string | null;
  sessions: { id: string; title: string }[];
  tasks: { id: string; title: string }[];
  files: { id: string; filename: string }[];
}

type Tone = "positive" | "accent" | "muted";

function LinkedListItem<T>({
  label,
  tone,
  items,
  keyOf,
  labelOf,
}: {
  label: string;
  tone: Tone;
  items: T[];
  keyOf: (item: T) => string;
  labelOf: (item: T) => string;
}) {
  return (
    <div>
      <p className="mb-1 text-[11px] uppercase tracking-wide text-ink-faint">
        {label} · {items.length}
      </p>
      {items.length === 0 ? (
        <p className="text-xs text-ink-faint">None</p>
      ) : (
        <ul className="space-y-1">
          {items.map((item) => (
            <li key={keyOf(item)}>
              <StatusBadge label={labelOf(item)} tone={tone} />
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

function LinkInput({
  placeholder,
  value,
  onChange,
  onLink,
}: {
  placeholder: string;
  value: string;
  onChange: (value: string) => void;
  onLink: (value: string) => void;
}) {
  return (
    <div className="flex items-center gap-1">
      <Input
        placeholder={placeholder}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        onKeyDown={(e) => e.key === "Enter" && onLink(value)}
        className="text-xs"
      />
      <Button variant="ghost" size="sm" onClick={() => onLink(value)}>
        Link
      </Button>
    </div>
  );
}

export function ProjectsView() {
  const [projects, setProjects] = useState<Project[]>([]);
  const [showForm, setShowForm] = useState(false);
  const [newName, setNewName] = useState("");
  const [newDesc, setNewDesc] = useState("");
  const [expandedId, setExpandedId] = useState<string | null>(null);
  const [editBrief, setEditBrief] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [linkInputs, setLinkInputs] = useState<Record<string, string>>({});

  const refresh = useCallback(async () => {
    setLoading(true);
    const r = await api.listProjects();
    if (r.ok) setProjects(r.data);
    setLoading(false);
  }, []);

  useEffect(() => {
    refresh();
  }, [refresh]);

  const create = async () => {
    if (!newName.trim()) return;
    const r = await api.createProject({
      name: newName.trim(),
      description: newDesc.trim() || undefined,
    });
    if (r.ok) {
      setNewName("");
      setNewDesc("");
      setShowForm(false);
      refresh();
    }
  };

  const archive = async (id: string) => {
    await api.updateProject(id, { status: "archived" });
    refresh();
  };

  const remove = async (id: string) => {
    await api.deleteProject(id);
    refresh();
  };

  const saveBrief = async (id: string, brief: string) => {
    await api.updateProject(id, { brief });
    setEditBrief(null);
    refresh();
  };

  const linkItem = async (
    id: string,
    kind: "session_ids" | "task_ids" | "file_ids",
    value: string,
  ) => {
    const trimmed = value.trim();
    if (!trimmed) return;
    await api.updateProject(id, { [kind]: [trimmed] });
    setLinkInputs((prev) => ({ ...prev, [id + kind]: "" }));
    refresh();
  };

  const statusTone = (s: string): "positive" | "accent" | "muted" => {
    if (s === "active") return "positive";
    if (s === "completed") return "accent";
    return "muted";
  };

  return (
    <PageContainer
      title="Projects"
      subtitle="Spaces where Miori keeps long-running work."
      actions={
        <Button
          variant="primary"
          size="sm"
          onClick={() => setShowForm((v) => !v)}
        >
          <Plus size={14} className="mr-1" />
          New Project
        </Button>
      }
    >
      <AnimatePresence>
        {showForm && (
          <motion.div
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: "auto" }}
            exit={{ opacity: 0, height: 0 }}
            className="mb-6 overflow-hidden"
          >
            <Card>
              <div className="space-y-3">
                <Input
                  placeholder="Project name…"
                  value={newName}
                  onChange={(e) => setNewName(e.target.value)}
                  onKeyDown={(e) => e.key === "Enter" && create()}
                />
                <Textarea
                  placeholder="Brief description (optional)…"
                  value={newDesc}
                  rows={2}
                  onChange={(e) => setNewDesc(e.target.value)}
                />
                <div className="flex justify-end gap-2">
                  <Button variant="ghost" size="sm" onClick={() => setShowForm(false)}>
                    Cancel
                  </Button>
                  <Button variant="primary" size="sm" onClick={create} disabled={!newName.trim()}>
                    Create
                  </Button>
                </div>
              </div>
            </Card>
          </motion.div>
        )}
      </AnimatePresence>

      {loading && projects.length === 0 ? (
        <div className="glass-soft rounded-lg px-6 py-16 text-center">
          <p className="text-sm text-ink-faint animate-pulse">Loading projects…</p>
        </div>
      ) : projects.length === 0 ? (
        <div className="glass-soft rounded-lg px-6 py-16 text-center">
          <FolderOpen size={32} className="mx-auto mb-3 text-ink-faint" />
          <p className="text-sm text-ink-soft">No projects yet.</p>
          <p className="mt-1 text-xs text-ink-faint">
            Create one to give Miori context for a long-running piece of work.
          </p>
        </div>
      ) : (
        <div className="space-y-3">
          {projects.map((p) => (
            <motion.div
              key={p.id}
              layout
              initial={{ opacity: 0, y: 8 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -8 }}
            >
              <Card className="transition-colors hover:border-accent/20">
                <CardHeader>
                  <div className="flex items-center gap-2">
                    <FileText size={16} className="text-accent" />
                    <CardTitle>{p.name}</CardTitle>
                    <StatusBadge label={p.status} tone={statusTone(p.status)} />
                  </div>
                  <div className="flex items-center gap-1">
                    <Button
                      variant="ghost"
                      size="icon"
                      title="Toggle brief"
                      onClick={() =>
                        setExpandedId(expandedId === p.id ? null : p.id)
                      }
                    >
                      <Pencil size={14} />
                    </Button>
                    <Button
                      variant="ghost"
                      size="icon"
                      title="Archive"
                      onClick={() => archive(p.id)}
                    >
                      <Archive size={14} />
                    </Button>
                    <Button
                      variant="ghost"
                      size="icon"
                      title="Delete"
                      onClick={() => remove(p.id)}
                    >
                      <Trash2 size={14} className="text-red-400" />
                    </Button>
                  </div>
                </CardHeader>
                {p.description && (
                  <CardBody>
                    <p className="text-xs text-ink-faint">{p.description}</p>
                  </CardBody>
                )}
                <AnimatePresence>
                  {expandedId === p.id && (
                    <motion.div
                      initial={{ opacity: 0, height: 0 }}
                      animate={{ opacity: 1, height: "auto" }}
                      exit={{ opacity: 0, height: 0 }}
                      className="mt-3 overflow-hidden"
                    >
                      <Textarea
                        placeholder="Project brief — Miori will remember this context…"
                        value={editBrief ?? p.brief ?? ""}
                        rows={4}
                        onChange={(e) => setEditBrief(e.target.value)}
                        className="text-xs"
                      />
                       <div className="mt-2 flex justify-end gap-2">
                         <Button
                           variant="ghost"
                           size="sm"
                           onClick={() => {
                             setEditBrief(null);
                             setExpandedId(null);
                           }}
                         >
                           Cancel
                         </Button>
                         <Button
                           variant="primary"
                           size="sm"
                           onClick={() => saveBrief(p.id, editBrief ?? p.brief ?? "")}
                         >
                           Save Brief
                         </Button>
                       </div>
                       <div className="mt-4 space-y-3 border-t border-white/5 pt-3">
                         <p className="text-xs font-medium text-ink-soft">
                           Linked items
                         </p>
                         <div className="grid grid-cols-1 gap-2 sm:grid-cols-3">
                           <LinkedListItem
                             label="Sessions"
                             tone="accent"
                             items={p.sessions}
                             keyOf={(s) => s.id}
                             labelOf={(s) => s.title}
                           />
                           <LinkedListItem
                             label="Tasks"
                             tone="positive"
                             items={p.tasks}
                             keyOf={(t) => t.id}
                             labelOf={(t) => t.title}
                           />
                           <LinkedListItem
                             label="Files"
                             tone="muted"
                             items={p.files}
                             keyOf={(f) => f.id}
                             labelOf={(f) => f.filename}
                           />
                         </div>
                         <div className="grid grid-cols-1 gap-2 sm:grid-cols-3">
                           <LinkInput
                             placeholder="Session id…"
                             value={linkInputs[p.id + "session_ids"] ?? ""}
                             onChange={(v) =>
                               setLinkInputs((prev) => ({
                                 ...prev,
                                 [p.id + "session_ids"]: v,
                               }))
                             }
                             onLink={(v) => linkItem(p.id, "session_ids", v)}
                           />
                           <LinkInput
                             placeholder="Task id…"
                             value={linkInputs[p.id + "task_ids"] ?? ""}
                             onChange={(v) =>
                               setLinkInputs((prev) => ({
                                 ...prev,
                                 [p.id + "task_ids"]: v,
                               }))
                             }
                             onLink={(v) => linkItem(p.id, "task_ids", v)}
                           />
                           <LinkInput
                             placeholder="File id…"
                             value={linkInputs[p.id + "file_ids"] ?? ""}
                             onChange={(v) =>
                               setLinkInputs((prev) => ({
                                 ...prev,
                                 [p.id + "file_ids"]: v,
                               }))
                             }
                             onLink={(v) => linkItem(p.id, "file_ids", v)}
                           />
                         </div>
                       </div>
                     </motion.div>
                  )}
                </AnimatePresence>
              </Card>
            </motion.div>
          ))}
        </div>
      )}
    </PageContainer>
  );
}

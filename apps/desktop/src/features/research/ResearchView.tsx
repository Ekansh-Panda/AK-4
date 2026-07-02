import { useEffect, useState, useCallback } from "react";
import { motion } from "framer-motion";
import { Plus, Trash2, Search, Loader2, BookOpen } from "lucide-react";
import { PageContainer } from "@/components/layout/PageContainer";
import { Button } from "@/components/ui/Button";
import { Card, CardHeader, CardTitle, CardBody } from "@/components/ui/Card";
import { Input } from "@/components/ui/Input";
import { StatusBadge } from "@/components/ui/StatusBadge";
import { ScrollArea } from "@/components/ui/ScrollArea";
import { api } from "@/lib/api";
import { cn } from "@/lib/cn";

interface ResearchSession {
  id: string;
  query: string;
  status: string;
  findings: string | null;
  sources: string | null;
  created_at: string | null;
  updated_at: string | null;
}

export function ResearchView() {
  const [sessions, setSessions] = useState<ResearchSession[]>([]);
  const [query, setQuery] = useState("");
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [detail, setDetail] = useState<ResearchSession | null>(null);
  const [loading, setLoading] = useState(true);
  const [launching, setLaunching] = useState(false);

  const refresh = useCallback(async () => {
    setLoading(true);
    const r = await api.listResearch();
    if (r.ok) setSessions(r.data);
    setLoading(false);
  }, []);

  useEffect(() => {
    refresh();
  }, [refresh]);

  // Poll for running sessions
  useEffect(() => {
    const hasRunning = sessions.some((s) => s.status === "running" || s.status === "pending");
    if (!hasRunning) return;
    const timer = setInterval(refresh, 3000);
    return () => clearInterval(timer);
  }, [sessions, refresh]);

  const launch = async () => {
    if (!query.trim() || launching) return;
    setLaunching(true);
    const r = await api.createResearch(query.trim());
    if (r.ok) {
      setQuery("");
      refresh();
    }
    setLaunching(false);
  };

  const viewDetail = async (id: string) => {
    setSelectedId(id);
    const r = await api.getResearch(id);
    if (r.ok) setDetail(r.data);
  };

  const remove = async (id: string) => {
    await api.deleteResearch(id);
    if (selectedId === id) {
      setSelectedId(null);
      setDetail(null);
    }
    refresh();
  };

  const statusTone = (s: string): "positive" | "accent" | "muted" => {
    if (s === "done") return "positive";
    if (s === "running") return "accent";
    return "muted";
  };

  return (
    <PageContainer
      title="Research"
      subtitle="Deep dives Miori runs and remembers."
    >
      {/* Launch bar */}
      <div className="mb-6">
        <Card>
          <div className="flex items-center gap-2">
            <Search size={16} className="text-ink-faint flex-shrink-0" />
            <Input
              placeholder="Ask Miori to research something…"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && launch()}
              className="border-0 bg-transparent focus:bg-transparent"
            />
            <Button
              variant="primary"
              size="sm"
              disabled={!query.trim() || launching}
              onClick={launch}
            >
              {launching ? (
                <Loader2 size={14} className="animate-spin" />
              ) : (
                <>
                  <Plus size={14} className="mr-1" /> Research
                </>
              )}
            </Button>
          </div>
        </Card>
      </div>

      <div className="flex gap-4" style={{ minHeight: "400px" }}>
        {/* Session list */}
        <div className="w-1/3 space-y-2">
          {loading && sessions.length === 0 ? (
            <div className="glass-soft rounded-lg px-4 py-10 text-center">
              <p className="text-sm text-ink-faint animate-pulse">Loading…</p>
            </div>
          ) : sessions.length === 0 ? (
            <div className="glass-soft rounded-lg px-4 py-10 text-center">
              <BookOpen size={24} className="mx-auto mb-2 text-ink-faint" />
              <p className="text-xs text-ink-faint">No research sessions yet.</p>
            </div>
          ) : (
            sessions.map((s) => (
              <motion.div
                key={s.id}
                initial={{ opacity: 0, x: -8 }}
                animate={{ opacity: 1, x: 0 }}
              >
                <Card
                  className={cn(
                    "cursor-pointer transition-colors",
                    selectedId === s.id
                      ? "border border-accent/30 bg-accent/5"
                      : "hover:border-accent/10"
                  )}
                  onClick={() => viewDetail(s.id)}
                >
                  <div className="flex items-start justify-between gap-2">
                    <div className="min-w-0 flex-1">
                      <p className="truncate text-xs font-medium text-ink">
                        {s.query}
                      </p>
                      <div className="mt-1 flex items-center gap-2">
                        <StatusBadge label={s.status} tone={statusTone(s.status)} />
                        {s.status === "running" && (
                          <Loader2 size={12} className="animate-spin text-accent" />
                        )}
                      </div>
                    </div>
                    <Button
                      variant="ghost"
                      size="icon"
                      title="Delete"
                      onClick={(e) => {
                        e.stopPropagation();
                        remove(s.id);
                      }}
                    >
                      <Trash2 size={12} className="text-red-400" />
                    </Button>
                  </div>
                </Card>
              </motion.div>
            ))
          )}
        </div>

        {/* Detail pane */}
        <div className="flex-1">
          {detail && selectedId ? (
            <motion.div
              key={detail.id}
              initial={{ opacity: 0, y: 8 }}
              animate={{ opacity: 1, y: 0 }}
            >
              <Card className="h-full">
                <CardHeader>
                  <CardTitle>{detail.query}</CardTitle>
                  <StatusBadge label={detail.status} tone={statusTone(detail.status)} />
                </CardHeader>
                <CardBody>
                  <ScrollArea className="max-h-[500px]">
                    {detail.status === "running" || detail.status === "pending" ? (
                      <div className="flex items-center gap-2 py-8 text-sm text-ink-faint">
                        <Loader2 size={16} className="animate-spin" />
                        Miori is researching…
                      </div>
                    ) : detail.findings ? (
                      <div className="prose prose-sm prose-invert max-w-none whitespace-pre-wrap text-xs leading-relaxed text-ink-soft">
                        {detail.findings}
                      </div>
                    ) : (
                      <p className="py-8 text-center text-xs text-ink-faint">
                        No findings yet.
                      </p>
                    )}
                  </ScrollArea>
                </CardBody>
              </Card>
            </motion.div>
          ) : (
            <div className="glass-soft flex h-full items-center justify-center rounded-lg">
              <p className="text-xs text-ink-faint">
                Select a session to view findings.
              </p>
            </div>
          )}
        </div>
      </div>
    </PageContainer>
  );
}

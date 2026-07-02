import { useEffect, useState } from "react";
import {
  UploadCloud,
  FileText,
  Image as ImageIcon,
  Music,
  File as FileIcon,
  Trash2,
  X,
  Search,
} from "lucide-react";
import { PageContainer } from "@/components/layout/PageContainer";
import { Input } from "@/components/ui/Input";
import { Button } from "@/components/ui/Button";
import { ScrollArea } from "@/components/ui/ScrollArea";
import { api } from "@/lib/api";
import { cn } from "@/lib/cn";
import type { ApiFile, ApiFileDetail } from "@/lib/types";

const kindIcon = {
  doc: FileText,
  image: ImageIcon,
  audio: Music,
  other: FileIcon,
} as const;

type Kind = keyof typeof kindIcon;

function formatSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(0)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

function inferKind(f: ApiFile): Kind {
  const ct = (f.content_type ?? "").toLowerCase();
  if (ct.startsWith("image/")) return "image";
  if (ct.startsWith("audio/")) return "audio";
  const ext = f.filename.split(".").pop()?.toLowerCase() ?? "";
  if (["png", "jpg", "jpeg", "gif", "webp", "svg"].includes(ext)) return "image";
  if (["mp3", "m4a", "wav", "ogg", "flac"].includes(ext)) return "audio";
  if (["pdf", "txt", "md", "doc", "docx"].includes(ext)) return "doc";
  return "other";
}

const MAX_BYTES = 25 * 1024 * 1024; // backend limit (413 on oversize)

export function FilesView() {
  const [files, setFiles] = useState<ApiFile[]>([]);
  const [dragging, setDragging] = useState(false);
  const [notice, setNotice] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [detail, setDetail] = useState<ApiFileDetail | null>(null);
  const [offline, setOffline] = useState(false);
  const [query, setQuery] = useState("");

  const load = async () => {
    const r = await api.listFiles();
    setOffline(!r.ok);
    setFiles(r.data);
  };

  useEffect(() => {
    const handler = setTimeout(() => {
      if (query.trim()) {
        api.searchFiles(query.trim()).then((r) => {
          setOffline(!r.ok);
          setFiles(r.data);
        });
      } else {
        load();
      }
    }, 300);
    return () => clearTimeout(handler);
  }, [query]);

  const upload = async (list: FileList | null) => {
    if (!list || list.length === 0) return;
    setNotice(null);
    setBusy(true);
    try {
      for (const file of Array.from(list)) {
        if (file.size > MAX_BYTES) {
          setNotice(
            `"${file.name}" is ${formatSize(file.size)} — over the 25 MB limit.`,
          );
          continue;
        }
        const r = await api.uploadFile(file);
        if (r.status === 413) {
          setNotice(`"${file.name}" was rejected by the server (too large).`);
          continue;
        }
        if (!r.ok || !r.data) {
          setNotice(`Couldn't upload "${file.name}" — backend unreachable.`);
          continue;
        }
      }
      await load();
    } finally {
      setBusy(false);
    }
  };

  const remove = async (id: string) => {
    const r = await api.deleteFile(id);
    if (!r.ok) {
      setNotice("Delete failed — backend unreachable.");
      return;
    }
    if (detail?.id === id) setDetail(null);
    await load();
  };

  const openDetail = async (id: string) => {
    const r = await api.fileDetail(id);
    if (r.ok && r.data) setDetail(r.data);
    else setNotice("Couldn't load file details — backend unreachable.");
  };

  return (
    <PageContainer title="Files" subtitle="Things you've shared with Miori.">
      {/* Dropzone */}
      <label
        onDragOver={(e) => {
          e.preventDefault();
          setDragging(true);
        }}
        onDragLeave={() => setDragging(false)}
        onDrop={(e) => {
          e.preventDefault();
          setDragging(false);
          void upload(e.dataTransfer.files);
        }}
        className={cn(
          "mb-4 flex cursor-pointer flex-col items-center justify-center gap-2 rounded-lg border border-dashed py-10 transition-colors",
          dragging
            ? "border-accent/60 bg-accent/5"
            : "border-white/[0.12] hover:border-white/20 hover:bg-white/[0.02]",
        )}
      >
        <UploadCloud size={24} className="text-accent" />
        <span className="text-sm text-ink-soft">
          {busy ? "Uploading…" : "Drop files here or click to upload"}
        </span>
        <span className="text-xs text-ink-faint">Max 25 MB per file</span>
        <input
          type="file"
          multiple
          className="hidden"
          disabled={busy}
          onChange={(e) => void upload(e.target.files)}
        />
      </label>

      {/* Search */}
      <div className="mb-6 flex items-center gap-2">
        <Input
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="Search files…"
          className="flex-1"
        />
        <Button variant="ghost" size="icon" disabled>
          <Search size={16} />
        </Button>
      </div>

      {notice && (
        <div className="mb-4 rounded border border-warn/40 bg-warn/10 px-4 py-2 text-xs text-ink-soft">
          {notice}
        </div>
      )}
      {offline && (
        <p className="mb-4 text-xs text-ink-faint">
          Backend unreachable — showing a local fallback list.
        </p>
      )}

      {/* List */}
      <ul className="space-y-2">
        {files.map((f) => {
          const kind = inferKind(f);
          const Icon = kindIcon[kind];
          return (
            <li
              key={f.id}
              className="glass-soft flex items-center gap-3 rounded px-4 py-3"
            >
              <Icon size={18} className="text-ink-faint shrink-0" />
              <button
                onClick={() => void openDetail(f.id)}
                className="min-w-0 flex-1 truncate text-left text-sm text-ink hover:text-accent"
                title="Open details"
              >
                {f.filename}
              </button>
              {f.has_text && (
                <span className="rounded-full bg-accent/10 px-2 py-0.5 text-[0.6rem] text-accent">
                  text
                </span>
              )}
              <span className="text-xs text-ink-faint">{formatSize(f.size_bytes)}</span>
              <button
                onClick={() => void remove(f.id)}
                aria-label="Delete file"
                className="text-ink-faint transition-colors hover:text-danger"
              >
                <Trash2 size={15} />
              </button>
            </li>
          );
        })}
        {files.length === 0 && <li className="text-sm text-ink-faint">No files yet.</li>}
      </ul>

      {/* Detail preview */}
      {detail && (
        <div className="fixed inset-0 z-40 flex items-center justify-center bg-black/50 p-6">
          <div className="glass flex max-h-[80vh] w-full max-w-2xl flex-col rounded-lg">
            <div className="flex items-center justify-between border-b hairline px-5 py-3">
              <div className="min-w-0">
                <h3 className="truncate text-sm font-medium text-ink">{detail.filename}</h3>
                <p className="text-xs text-ink-faint">
                  {detail.content_type ?? "unknown"} · {formatSize(detail.size_bytes)} ·{" "}
                  {detail.status}
                </p>
              </div>
              <Button
                variant="ghost"
                size="icon"
                aria-label="Close"
                onClick={() => setDetail(null)}
              >
                <X size={18} />
              </Button>
            </div>
            <ScrollArea className="flex-1 px-5 py-4">
              {detail.has_text && detail.extracted_text ? (
                <pre className="whitespace-pre-wrap text-xs leading-relaxed text-ink-soft">
                  {detail.extracted_text}
                </pre>
              ) : (
                <p className="text-sm text-ink-faint">
                  No extracted text available for this file.
                </p>
              )}
            </ScrollArea>
          </div>
        </div>
      )}
    </PageContainer>
  );
}

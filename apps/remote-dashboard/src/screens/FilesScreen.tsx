import { useCallback, useEffect, useRef, useState } from "react";
import { UploadCloud, File as FileIcon, CheckCircle2, X } from "lucide-react";
import { Button } from "@/components/Button";
import { GlassCard } from "@/components/GlassCard";
import { ScreenHeader } from "@/components/ScreenHeader";
import { getFiles, uploadFile } from "@/lib/api";
import { useConnection } from "@/state/connection";
import type { HostFile, UploadResult } from "@/lib/types";

type Phase = "idle" | "uploading" | "done" | "error";

/**
 * Upload a file from the phone to the host (POST /api/files, multipart) with
 * real XHR progress, and list what's already on the host (GET /api/files).
 * Falls back to an animated mock + canned listing when the host is unreachable.
 */
export function FilesScreen() {
  const { host, token, isMock } = useConnection();
  const inputRef = useRef<HTMLInputElement>(null);
  const abortRef = useRef<AbortController | null>(null);

  const [file, setFile] = useState<File | null>(null);
  const [phase, setPhase] = useState<Phase>("idle");
  const [percent, setPercent] = useState(0);
  const [result, setResult] = useState<UploadResult | null>(null);
  const [files, setFiles] = useState<HostFile[]>([]);

  const loadFiles = useCallback(async () => {
    setFiles(await getFiles({ host, token }));
  }, [host, token]);

  useEffect(() => {
    void loadFiles();
  }, [loadFiles]);

  function pick() {
    inputRef.current?.click();
  }

  async function onFile(e: React.ChangeEvent<HTMLInputElement>) {
    const f = e.target.files?.[0];
    if (!f) return;
    setFile(f);
    setResult(null);
    setPercent(0);
    setPhase("uploading");

    const controller = new AbortController();
    abortRef.current = controller;
    const res = await uploadFile(
      { host, token },
      f,
      (p) => setPercent(p.percent),
      controller.signal,
    );
    setResult(res);
    setPhase(res.ok ? "done" : "error");
    abortRef.current = null;
    // Allow re-picking the same file.
    e.target.value = "";
    // Refresh the host listing after a successful upload.
    if (res.ok) void loadFiles();
  }

  function reset() {
    abortRef.current?.abort();
    setFile(null);
    setPhase("idle");
    setPercent(0);
    setResult(null);
  }

  return (
    <main className="flex min-h-dvh flex-col">
      <ScreenHeader title="Files" subtitle="Send something to the host" />

      <div className="mx-auto w-full max-w-md flex-1 px-5 pb-28">
        <input
          ref={inputRef}
          type="file"
          className="hidden"
          onChange={onFile}
        />

        {phase === "idle" && (
          <button
            onClick={pick}
            className="glass flex w-full flex-col items-center gap-3 rounded-2xl border-dashed border-white/[0.12] px-6 py-12 text-center transition-colors hover:border-accent/40 hover:bg-accent/[0.04]"
          >
            <span className="grid h-14 w-14 place-items-center rounded-full bg-accent/15 text-accent-soft">
              <UploadCloud className="h-7 w-7" aria-hidden />
            </span>
            <span className="font-medium">Choose a file</span>
            <span className="max-w-[16rem] text-sm text-ink-soft">
              Pick anything from your phone and I'll carry it over to the host.
            </span>
          </button>
        )}

        {phase !== "idle" && file && (
          <GlassCard elevated className="flex flex-col gap-4">
            <div className="flex items-center gap-3">
              <span className="grid h-11 w-11 shrink-0 place-items-center rounded-xl bg-white/[0.06]">
                {phase === "done" ? (
                  <CheckCircle2 className="h-5 w-5 text-positive" aria-hidden />
                ) : (
                  <FileIcon className="h-5 w-5 text-ink-soft" aria-hidden />
                )}
              </span>
              <div className="min-w-0 flex-1">
                <p className="truncate font-medium">{file.name}</p>
                <p className="text-xs text-ink-faint">
                  {formatBytes(file.size)}
                </p>
              </div>
              <button
                onClick={reset}
                className="grid h-9 w-9 place-items-center rounded-full text-ink-faint transition-colors hover:bg-white/[0.06] hover:text-ink"
                aria-label="Clear"
              >
                <X className="h-4 w-4" aria-hidden />
              </button>
            </div>

            {/* Progress */}
            <div>
              <div className="h-2 overflow-hidden rounded-full bg-white/[0.06]">
                <div
                  className="h-full rounded-full bg-accent transition-[width] duration-150 ease-soft"
                  style={{ width: `${percent}%` }}
                />
              </div>
              <p className="mt-1.5 text-xs text-ink-soft">
                {phase === "uploading" && `Sending… ${percent}%`}
                {phase === "done" &&
                  (isMock
                    ? "Delivered (offline mock)."
                    : "Delivered to the host.")}
                {phase === "error" && (
                  <span className="text-danger">
                    {result?.error ?? "Upload failed."}
                  </span>
                )}
              </p>
            </div>

            {phase !== "uploading" && (
              <Button variant="ghost" full onClick={reset}>
                Send another
              </Button>
            )}
          </GlassCard>
        )}

        {/* Host listing */}
        <section className="mt-5">
          <h2 className="mb-2 px-1 text-sm font-semibold text-ink-soft">
            On the host
          </h2>
          {files.length === 0 ? (
            <GlassCard className="text-center text-sm text-ink-faint">
              Nothing here yet — your uploads will show up here.
            </GlassCard>
          ) : (
            <div className="flex flex-col gap-2">
              {files.map((f) => (
                <GlassCard key={f.id} className="flex items-center gap-3 py-3">
                  <span className="grid h-9 w-9 shrink-0 place-items-center rounded-lg bg-white/[0.06]">
                    <FileIcon className="h-4 w-4 text-ink-soft" aria-hidden />
                  </span>
                  <div className="min-w-0 flex-1">
                    <p className="truncate text-sm font-medium">{f.filename}</p>
                    <p className="text-xs text-ink-faint">
                      {formatBytes(f.sizeBytes)}
                      {f.contentType ? ` · ${f.contentType}` : ""}
                    </p>
                  </div>
                  <span className="shrink-0 rounded-full bg-white/[0.05] px-2.5 py-1 text-[10px] font-medium uppercase tracking-wide text-ink-soft">
                    {f.status}
                  </span>
                </GlassCard>
              ))}
            </div>
          )}
        </section>

        {isMock && (
          <p className="mt-5 rounded-xl border border-warn/25 bg-warn/[0.06] px-4 py-2.5 text-center text-xs text-warn">
            Offline — uploads are simulated and the listing is canned. Connect to
            a reachable host to send files for real.
          </p>
        )}
      </div>
    </main>
  );
}

function formatBytes(bytes: number): string {
  if (bytes === 0) return "0 B";
  const units = ["B", "KB", "MB", "GB"];
  const i = Math.floor(Math.log(bytes) / Math.log(1024));
  return `${(bytes / Math.pow(1024, i)).toFixed(i === 0 ? 0 : 1)} ${units[i]}`;
}

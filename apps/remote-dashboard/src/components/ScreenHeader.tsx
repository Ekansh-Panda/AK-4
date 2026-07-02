import type { ReactNode } from "react";
import { ConnectionChip } from "./ConnectionChip";

/**
 * Shared sticky header for tabbed screens: title + subtitle on the left, the
 * persistent connection chip on the right.
 */
export function ScreenHeader({
  title,
  subtitle,
  right,
}: {
  title: string;
  subtitle?: string;
  right?: ReactNode;
}) {
  return (
    <header className="sticky top-0 z-20 px-5 pt-safe">
      <div className="flex items-start justify-between gap-3 py-4">
        <div>
          <h1 className="text-xl font-semibold tracking-tight">{title}</h1>
          {subtitle && (
            <p className="mt-0.5 text-sm text-ink-soft">{subtitle}</p>
          )}
        </div>
        <div className="pt-1">{right ?? <ConnectionChip />}</div>
      </div>
    </header>
  );
}

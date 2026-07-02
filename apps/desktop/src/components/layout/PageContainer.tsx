import { type ReactNode } from "react";
import { ScrollArea } from "@/components/ui/ScrollArea";

export interface PageContainerProps {
  title: string;
  subtitle?: string;
  /** Optional actions rendered to the right of the title. */
  actions?: ReactNode;
  children: ReactNode;
}

/** Consistent padded, scrollable frame for the non-chat feature views. */
export function PageContainer({ title, subtitle, actions, children }: PageContainerProps) {
  return (
    <ScrollArea className="h-full">
      <div className="mx-auto max-w-4xl px-8 py-8 animate-fade-up">
        <header className="mb-6 flex items-start justify-between gap-4">
          <div>
            <h2 className="text-lg font-medium text-ink">{title}</h2>
            {subtitle && <p className="mt-1 text-sm text-ink-faint">{subtitle}</p>}
          </div>
          {actions}
        </header>
        {children}
      </div>
    </ScrollArea>
  );
}

/** Centered placeholder used by not-yet-built views. */
export function ComingSoon({ note }: { note: string }) {
  return (
    <div className="glass-soft rounded-lg px-6 py-16 text-center">
      <p className="text-sm text-ink-soft">{note}</p>
      <p className="mt-1 text-xs text-ink-faint">Coming in a later build.</p>
    </div>
  );
}

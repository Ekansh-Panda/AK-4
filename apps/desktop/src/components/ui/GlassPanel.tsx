import { forwardRef, type HTMLAttributes } from "react";
import { cn } from "@/lib/cn";

export interface GlassPanelProps extends HTMLAttributes<HTMLDivElement> {
  /** Use the lighter "soft" glass recipe. */
  soft?: boolean;
}

/**
 * The core surface primitive. Everything floating in the shell sits on glass.
 */
export const GlassPanel = forwardRef<HTMLDivElement, GlassPanelProps>(
  ({ className, soft, ...props }, ref) => (
    <div
      ref={ref}
      className={cn(soft ? "glass-soft" : "glass", "rounded-lg", className)}
      {...props}
    />
  ),
);
GlassPanel.displayName = "GlassPanel";

import type { HTMLAttributes, ReactNode } from "react";
import { cn } from "@/lib/cn";

interface GlassCardProps extends HTMLAttributes<HTMLDivElement> {
  elevated?: boolean;
  children: ReactNode;
}

/** The core frosted surface. Wraps the `.glass` component classes. */
export function GlassCard({
  elevated = false,
  className,
  children,
  ...rest
}: GlassCardProps) {
  return (
    <div
      className={cn(
        elevated ? "glass-elevated" : "glass",
        "rounded-2xl p-4",
        className,
      )}
      {...rest}
    >
      {children}
    </div>
  );
}

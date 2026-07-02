import { type HTMLAttributes } from "react";
import { cn } from "@/lib/cn";

/**
 * Self-contained scroll container. Relies on the themed native scrollbars
 * defined in index.css — no Radix/shadcn dependency.
 */
export function ScrollArea({ className, children, ...props }: HTMLAttributes<HTMLDivElement>) {
  return (
    <div className={cn("min-h-0 overflow-y-auto overflow-x-hidden", className)} {...props}>
      {children}
    </div>
  );
}

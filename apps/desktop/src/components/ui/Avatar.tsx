import { cn } from "@/lib/cn";

export interface AvatarProps {
  /** "miori" renders the warm orb glyph; otherwise initials. */
  who: "miori" | "user" | "system";
  size?: number;
  className?: string;
}

export function Avatar({ who, size = 32, className }: AvatarProps) {
  const dim = { width: size, height: size };
  if (who === "miori") {
    return (
      <div
        style={dim}
        className={cn(
          "rounded-full bg-gradient-to-br from-accent to-accent-soft",
          "shadow-glow shrink-0",
          className,
        )}
        aria-hidden
      />
    );
  }
  return (
    <div
      style={dim}
      className={cn(
        "rounded-full grid place-items-center shrink-0 text-xs font-medium",
        "bg-white/[0.06] text-ink-soft border border-white/[0.08]",
        className,
      )}
      aria-hidden
    >
      {who === "user" ? "You" : "·"}
    </div>
  );
}

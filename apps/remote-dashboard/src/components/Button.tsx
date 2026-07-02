import { forwardRef, type ButtonHTMLAttributes } from "react";
import { Loader2 } from "lucide-react";
import { cn } from "@/lib/cn";

type Variant = "primary" | "ghost" | "danger" | "subtle";
type Size = "md" | "lg";

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: Variant;
  size?: Size;
  loading?: boolean;
  full?: boolean;
}

const VARIANTS: Record<Variant, string> = {
  primary:
    "bg-accent text-canvas font-medium shadow-glow hover:bg-accent-soft active:scale-[0.985]",
  ghost:
    "bg-white/[0.04] text-ink border border-white/[0.08] hover:bg-white/[0.07] active:scale-[0.985]",
  subtle: "bg-transparent text-ink-soft hover:text-ink hover:bg-white/[0.05]",
  danger:
    "bg-danger/15 text-danger border border-danger/30 hover:bg-danger/25 active:scale-[0.985]",
};

const SIZES: Record<Size, string> = {
  // Generous touch targets — minimum 44px tall.
  md: "h-11 px-4 text-sm rounded-xl gap-2",
  lg: "h-14 px-5 text-base rounded-2xl gap-2.5",
};

/** App button. Big, tappable, calm motion. */
export const Button = forwardRef<HTMLButtonElement, ButtonProps>(
  (
    {
      variant = "primary",
      size = "md",
      loading = false,
      full = false,
      className,
      children,
      disabled,
      ...rest
    },
    ref,
  ) => {
    return (
      <button
        ref={ref}
        disabled={disabled || loading}
        className={cn(
          "inline-flex items-center justify-center transition-all duration-200 ease-soft select-none",
          "disabled:opacity-50 disabled:pointer-events-none",
          "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent/50",
          VARIANTS[variant],
          SIZES[size],
          full && "w-full",
          className,
        )}
        {...rest}
      >
        {loading && <Loader2 className="h-4 w-4 animate-spin" aria-hidden />}
        {children}
      </button>
    );
  },
);
Button.displayName = "Button";

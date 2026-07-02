import { forwardRef, type ButtonHTMLAttributes } from "react";
import { cn } from "@/lib/cn";

type Variant = "primary" | "ghost" | "subtle" | "danger";
type Size = "sm" | "md" | "icon";

export interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: Variant;
  size?: Size;
}

const variants: Record<Variant, string> = {
  primary:
    "bg-accent/90 text-canvas font-medium hover:bg-accent shadow-glow hover:shadow-glow",
  ghost: "text-ink-soft hover:text-ink hover:bg-white/5",
  subtle: "glass-soft text-ink-soft hover:text-ink hover:bg-white/[0.06]",
  danger: "text-danger hover:bg-danger/10",
};

const sizes: Record<Size, string> = {
  sm: "h-8 px-3 text-sm rounded-sm gap-1.5",
  md: "h-10 px-4 text-sm rounded gap-2",
  icon: "h-9 w-9 rounded-sm grid place-items-center",
};

export const Button = forwardRef<HTMLButtonElement, ButtonProps>(
  ({ className, variant = "subtle", size = "md", ...props }, ref) => (
    <button
      ref={ref}
      className={cn(
        "inline-flex items-center justify-center select-none",
        "transition-colors duration-200 ease-soft",
        "disabled:opacity-40 disabled:pointer-events-none",
        variants[variant],
        sizes[size],
        className,
      )}
      {...props}
    />
  ),
);
Button.displayName = "Button";

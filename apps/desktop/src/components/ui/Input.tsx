import { forwardRef, type InputHTMLAttributes, type TextareaHTMLAttributes } from "react";
import { cn } from "@/lib/cn";

const base =
  "w-full bg-white/[0.03] border border-white/[0.08] rounded text-sm text-ink " +
  "placeholder:text-ink-faint transition-colors duration-200 " +
  "focus:border-accent/50 focus:bg-white/[0.05] outline-none";

export const Input = forwardRef<HTMLInputElement, InputHTMLAttributes<HTMLInputElement>>(
  ({ className, ...props }, ref) => (
    <input ref={ref} className={cn(base, "h-10 px-3", className)} {...props} />
  ),
);
Input.displayName = "Input";

export const Textarea = forwardRef<
  HTMLTextAreaElement,
  TextareaHTMLAttributes<HTMLTextAreaElement>
>(({ className, ...props }, ref) => (
  <textarea ref={ref} className={cn(base, "px-3 py-2 resize-none leading-relaxed", className)} {...props} />
));
Textarea.displayName = "Textarea";

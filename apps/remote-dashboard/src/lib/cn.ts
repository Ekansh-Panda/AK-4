import clsx, { type ClassValue } from "clsx";

/**
 * Tiny class-name joiner. We keep it dependency-light (just `clsx`); no
 * tailwind-merge here — the dashboard's classes rarely conflict, and we'd
 * rather not pull extra weight onto a phone bundle.
 */
export function cn(...inputs: ClassValue[]): string {
  return clsx(inputs);
}

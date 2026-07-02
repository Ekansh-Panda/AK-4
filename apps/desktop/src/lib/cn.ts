import { clsx, type ClassValue } from "clsx";

/**
 * Tiny className combiner. Kept dependency-light on purpose (no tailwind-merge);
 * author classes so conflicting utilities don't collide in the same element.
 */
export function cn(...inputs: ClassValue[]): string {
  return clsx(inputs);
}

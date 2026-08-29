export function prefersReducedMotion(): boolean {
  if (typeof window === "undefined" || typeof window.matchMedia !== "function") return false;
  return window.matchMedia("(prefers-reduced-motion: reduce)").matches;
}

/** Standard product easing — editorial deceleration */
export const EASE = "cubic-bezier(0.22, 1, 0.36, 1)";

/** Enter — slightly more lift */
export const EASE_ENTER = "cubic-bezier(0.16, 1, 0.3, 1)";

/** Exit — quicker settle */
export const EASE_EXIT = "cubic-bezier(0.4, 0, 0.2, 1)";

/** Emphasis — for adaptation moments */
export const EASE_EMPHASIS = "cubic-bezier(0.34, 1.15, 0.64, 1)";

/** PathFinder motion grammar */
export const DURATION = {
  instant: 80,
  micro: 140,
  interaction: 220,
  transition: 360,
  signature: 720,
  hero: 880,
  /** @deprecated use instant/micro/interaction/transition/signature */
  fast: 140,
  normal: 220,
  slow: 360,
  cascade: 600,
} as const;

export const MIN_RESOLVE_MS = 420;

export async function withMinimumDuration<T>(startedAt: number, work: Promise<T>): Promise<T> {
  const [result] = await Promise.all([
    work,
    new Promise<void>((resolve) => {
      const elapsed = Date.now() - startedAt;
      const wait = Math.max(0, MIN_RESOLVE_MS - elapsed);
      window.setTimeout(resolve, wait);
    }),
  ]);
  return result;
}

export function staggerDelay(index: number, base = 48): number {
  return prefersReducedMotion() ? 0 : index * base;
}

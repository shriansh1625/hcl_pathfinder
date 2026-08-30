"use client";

import { useLayoutEffect, useRef, type ReactNode } from "react";
import { EASE, prefersReducedMotion } from "@/lib/motion";

export function FlipList({
  children,
  replay,
}: {
  children: ReactNode;
  replay: string;
}) {
  const root = useRef<HTMLDivElement>(null);
  const prior = useRef<Map<string, DOMRect>>(new Map());
  const viewportWidth = useRef(0);

  useLayoutEffect(() => {
    const node = root.current;
    if (!node) return;

    const width = window.innerWidth;
    const widthChanged = viewportWidth.current > 0 && Math.abs(width - viewportWidth.current) > 2;
    viewportWidth.current = width;

    const next = new Map<string, DOMRect>();
    node.querySelectorAll<HTMLElement>("[data-flip-key]").forEach((el) => {
      const key = el.dataset.flipKey;
      if (key) next.set(key, el.getBoundingClientRect());
    });

    if (!prefersReducedMotion() && !widthChanged) {
      const maxDx = Math.max(48, width * 0.12);
      next.forEach((rect, key) => {
        const before = prior.current.get(key);
        const el = Array.from(node.querySelectorAll<HTMLElement>("[data-flip-key]")).find(
          (candidate) => candidate.dataset.flipKey === key,
        );
        if (!before || !el) return;
        if (el.dataset.flipLock === "1") return;
        const dx = before.left - rect.left;
        const dy = before.top - rect.top;
        if (Math.abs(dx) < 0.5 && Math.abs(dy) < 0.5) return;
        // Cross-layout FLIP deltas (e.g. 1440→390) must not run — they spill past the viewport.
        if (Math.abs(dx) > maxDx) return;
        if (typeof el.animate === "function") {
          el.animate(
            [{ transform: `translate(${dx}px, ${dy}px)` }, { transform: "translate(0, 0)" }],
            { duration: 380, easing: EASE },
          );
        }
      });
    }

    prior.current = next;
  }, [replay]);

  return (
    <div ref={root} className="flip-list space-y-2">
      {children}
    </div>
  );
}
"use client";

import { prefersReducedMotion } from "@/lib/motion";
import { useTheme } from "@/lib/theme";
import { useEffect, useRef } from "react";

/** Layered ambient environment for homepage — both themes, pointer-responsive on desktop. */
export function HomeAmbience() {
  const { theme } = useTheme();
  const rootRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const root = rootRef.current?.closest(".home-landing") as HTMLElement | null;
    if (!root) return;

    root.dataset.ambience = theme;

    if (prefersReducedMotion() || window.matchMedia("(pointer: coarse)").matches) return;

    let frame = 0;
    let raf = 0;
    let px = 0.5;
    let py = 0.35;

    const apply = () => {
      frame = 0;
      root.style.setProperty("--home-px", px.toFixed(4));
      root.style.setProperty("--home-py", py.toFixed(4));
    };

    const onMove = (event: PointerEvent) => {
      const rect = root.getBoundingClientRect();
      px = (event.clientX - rect.left) / rect.width;
      py = (event.clientY - rect.top) / rect.height;
      if (frame) return;
      frame = 1;
      raf = window.requestAnimationFrame(apply);
    };

    root.addEventListener("pointermove", onMove, { passive: true });
    return () => {
      root.removeEventListener("pointermove", onMove);
      window.cancelAnimationFrame(raf);
      root.style.removeProperty("--home-px");
      root.style.removeProperty("--home-py");
      delete root.dataset.ambience;
    };
  }, [theme]);

  return (
    <div ref={rootRef} className={`home-ambience home-ambience-${theme}`} aria-hidden>
      <div className="home-ambience-base" />
      <div className="home-ambience-field home-ambience-field-a" />
      <div className="home-ambience-field home-ambience-field-b" />
      <div className="home-ambience-grid" />
      <div className="home-ambience-grain" />
      <div className="home-ambience-glow" />
    </div>
  );
}

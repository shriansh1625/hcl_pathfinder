"use client";

import { useTheme } from "@/lib/theme";
import { prefersReducedMotion } from "@/lib/motion";
import { useEffect, useRef } from "react";

/** Interactive parchment ambience — light theme homepage only. */
export function LightHomeAmbience() {
  const { theme } = useTheme();
  const rootRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (theme !== "light") return;
    const root = rootRef.current?.closest(".home-landing") as HTMLElement | null;
    if (!root) return;

    root.classList.add("home-landing-light");

    if (prefersReducedMotion()) return;

    let frame = 0;
    let raf = 0;
    let px = 0.5;
    let py = 0.5;

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
      root.classList.remove("home-landing-light");
      root.style.removeProperty("--home-px");
      root.style.removeProperty("--home-py");
    };
  }, [theme]);

  if (theme !== "light") return null;

  return (
    <div ref={rootRef} className="light-home-ambience" aria-hidden>
      <div className="light-home-orb light-home-orb-a" />
      <div className="light-home-orb light-home-orb-b" />
      <div className="light-home-orb light-home-orb-c" />
      <div className="light-home-topo" />
      <div className="light-home-shimmer" />
    </div>
  );
}

"use client";

import { useEffect } from "react";
import { prefersReducedMotion } from "@/lib/motion";

/** Desktop pointer field. Touch and reduced-motion do nothing. */
export function PointerField() {
  useEffect(() => {
    if (typeof window === "undefined") return;
    if (prefersReducedMotion()) return;
    if (window.matchMedia("(pointer: coarse)").matches) return;

    const root = document.documentElement;
    let frame = 0;
    let nextX = 0;
    let nextY = 0;
    let raf = 0;

    const apply = () => {
      frame = 0;
      root.style.setProperty("--pointer-x", nextX.toFixed(3));
      root.style.setProperty("--pointer-y", nextY.toFixed(3));
    };

    const onMove = (event: PointerEvent) => {
      nextX = (event.clientX / window.innerWidth - 0.5) * 2;
      nextY = (event.clientY / window.innerHeight - 0.5) * 2;
      if (frame) return;
      frame = 1;
      raf = window.requestAnimationFrame(apply);
    };

    window.addEventListener("pointermove", onMove, { passive: true });
    return () => {
      window.removeEventListener("pointermove", onMove);
      window.cancelAnimationFrame(raf);
      root.style.removeProperty("--pointer-x");
      root.style.removeProperty("--pointer-y");
    };
  }, []);

  return null;
}

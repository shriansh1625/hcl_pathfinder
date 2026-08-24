"use client";

import { useEffect, useState } from "react";
import { prefersReducedMotion } from "@/lib/motion";

type Props = {
  step: number;
  resolved: boolean;
  launching?: boolean;
};

export function AmbientPathGraph({ step, resolved, launching }: Props) {
  const [interactive, setInteractive] = useState(false);
  const progress = Math.min(1, (step + (resolved ? 0.35 : 0)) / 6.5);

  useEffect(() => {
    if (prefersReducedMotion()) return;
    const onMove = () => setInteractive(true);
    window.addEventListener("pointermove", onMove, { once: true });
    return () => window.removeEventListener("pointermove", onMove);
  }, []);

  return (
    <div
      className={`ambient-path ${interactive ? "is-interactive" : ""} ${launching ? "is-launching" : ""}`}
      aria-hidden
      style={{
        position: "absolute",
        top: "-2rem",
        left: "-1rem",
        right: "-1rem",
        height: "16rem",
        pointerEvents: "none",
        opacity: 0.35,
        overflow: "hidden",
        ["--path-progress" as string]: progress,
      }}
    >
      <svg
        className="ambient-path-svg"
        viewBox="0 0 420 300"
        preserveAspectRatio="xMidYMid slice"
        style={{ width: "100%", height: "100%", display: "block" }}
      >
        <path
          className="ambient-path-line"
          d="M 36 248 C 90 210, 120 170, 168 148 S 260 118, 312 92 S 360 68, 384 48"
          fill="none"
          stroke="rgba(197, 212, 203, 0.22)"
          strokeWidth="1"
        />
        <circle className="ambient-node n1" cx="36" cy="248" r="3" fill="rgba(197, 212, 203, 0.25)" />
        <circle className="ambient-node n2" cx="120" cy="168" r="3" fill="rgba(197, 212, 203, 0.25)" />
        <circle className="ambient-node n3" cx="200" cy="128" r="3" fill="rgba(197, 212, 203, 0.25)" />
        <circle className="ambient-node n4" cx="280" cy="100" r="3" fill="rgba(197, 212, 203, 0.25)" />
        <circle className="ambient-node dest" cx="384" cy="48" r="4.5" fill="rgba(197, 212, 203, 0.55)" />
      </svg>
    </div>
  );
}
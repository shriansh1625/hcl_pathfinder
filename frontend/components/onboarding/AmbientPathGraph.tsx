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
      className={`ambient-path ${interactive ? "is-interactive" : ""} ${launching ? "is-launching" : ""} ${resolved ? "is-resolved" : ""}`}
      aria-hidden
        style={{
        position: "absolute",
        top: "-1.5rem",
        left: "-2rem",
        right: "-2rem",
        height: "22rem",
        pointerEvents: "none",
        opacity: resolved ? 0.55 : 0.28,
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
          strokeWidth="1"
        />
        <circle className="ambient-node n1" cx="36" cy="248" r="3" />
        <circle className="ambient-node n2" cx="120" cy="168" r="3" />
        <circle className="ambient-node n3" cx="200" cy="128" r="3" />
        <circle className="ambient-node n4" cx="280" cy="100" r="3" />
        <circle className="ambient-node dest" cx="384" cy="48" r="4.5" />
      </svg>
    </div>
  );
}
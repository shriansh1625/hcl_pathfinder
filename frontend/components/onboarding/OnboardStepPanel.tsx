"use client";

import { useEffect, useRef, type ReactNode } from "react";

export function OnboardStepPanel({ step, children }: { step: number; children: ReactNode }) {
  const prev = useRef(step);
  const dir = step >= prev.current ? "fwd" : "back";

  useEffect(() => {
    prev.current = step;
  }, [step]);

  return (
    <div key={step} className={`onboard-step-panel onboard-step-${dir}`}>
      {children}
    </div>
  );
}
"use client";

import { useLayoutEffect, useRef } from "react";

const STEPS = ["Goal", "Career", "Experience", "Interests", "Schedule", "Evidence", "Profile"] as const;

export function OnboardStepRail({ step }: { step: number }) {
  const trackRef = useRef<HTMLOListElement>(null);
  const indicatorRef = useRef<HTMLSpanElement>(null);

  useLayoutEffect(() => {
    const track = trackRef.current;
    const indicator = indicatorRef.current;
    const active = track?.querySelector<HTMLElement>(".onboard-step-item.is-active");
    if (!track || !indicator || !active) return;
    const trackBox = track.getBoundingClientRect();
    const box = active.getBoundingClientRect();
    indicator.style.width = `${box.width}px`;
    indicator.style.transform = `translateX(${box.left - trackBox.left}px)`;
  }, [step]);

  return (
    <nav className="onboard-step-rail" aria-label="Onboarding progress">
      <ol
        ref={trackRef}
        className="onboard-step-track m-0 list-none p-0"
      >
        {STEPS.map((label, index) => {
          const state = index === step ? "active" : index < step ? "complete" : "upcoming";
          return (
            <li
              key={label}
              className={`onboard-step-item is-${state}`}
              aria-current={index === step ? "step" : undefined}
              aria-label={`Step ${index + 1}: ${label}`}
            >
              <span className="onboard-step-waypoint" aria-hidden />
              <span className="onboard-step-label">{label}</span>
            </li>
          );
        })}
        <span ref={indicatorRef} className="onboard-step-route-indicator" aria-hidden />
      </ol>
    </nav>
  );
}

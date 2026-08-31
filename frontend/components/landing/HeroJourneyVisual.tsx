"use client";

import Image from "next/image";
import { prefersReducedMotion } from "@/lib/motion";
import { useEffect, useRef, useState } from "react";

const HERO_IMAGE = "/images/pathfinder-hero-journey.png";
const IMAGE_WIDTH = 1536;
const IMAGE_HEIGHT = 1024;

export function HeroJourneyVisual() {
  const wrapRef = useRef<HTMLDivElement>(null);
  const [ready, setReady] = useState(false);

  useEffect(() => {
    if (prefersReducedMotion()) {
      setReady(true);
      return;
    }
    const t = window.requestAnimationFrame(() => setReady(true));
    return () => window.cancelAnimationFrame(t);
  }, []);

  useEffect(() => {
    if (prefersReducedMotion() || window.matchMedia("(pointer: coarse)").matches) return;
    const el = wrapRef.current;
    if (!el) return;

    let frame = 0;
    let raf = 0;
    let px = 0;
    let py = 0;

    const apply = () => {
      frame = 0;
      el.style.setProperty("--hero-parallax-x", `${px.toFixed(2)}px`);
      el.style.setProperty("--hero-parallax-y", `${py.toFixed(2)}px`);
    };

    const onMove = (event: PointerEvent) => {
      const rect = el.getBoundingClientRect();
      const cx = (event.clientX - rect.left) / rect.width - 0.5;
      const cy = (event.clientY - rect.top) / rect.height - 0.5;
      px = cx * 3;
      py = cy * -2;
      if (frame) return;
      frame = 1;
      raf = window.requestAnimationFrame(apply);
    };

    const onLeave = () => {
      px = 0;
      py = 0;
      raf = window.requestAnimationFrame(apply);
    };

    el.addEventListener("pointermove", onMove, { passive: true });
    el.addEventListener("pointerleave", onLeave);
    return () => {
      el.removeEventListener("pointermove", onMove);
      el.removeEventListener("pointerleave", onLeave);
      window.cancelAnimationFrame(raf);
    };
  }, []);

  return (
    <figure
      ref={wrapRef}
      className={`hero-illustration ${ready ? "is-ready" : ""}`}
      aria-label="PathFinder career journey illustration"
    >
      <div className="hero-illustration-aura" aria-hidden />
      <div className="hero-illustration-frame">
        <Image
          src={HERO_IMAGE}
          alt="A career journey from discovering your goal through evidence and personalized learning to your destination"
          width={IMAGE_WIDTH}
          height={IMAGE_HEIGHT}
          priority
          className="hero-illustration-img"
          sizes="(max-width: 768px) 100vw, (max-width: 1280px) 48vw, 560px"
        />
      </div>
      <figcaption className="hero-illustration-caption">
        Goal <span aria-hidden>→</span> Evidence <span aria-hidden>→</span> Diagnosis <span aria-hidden>→</span> Path{" "}
        <span aria-hidden>→</span> Career destination
      </figcaption>
    </figure>
  );
}

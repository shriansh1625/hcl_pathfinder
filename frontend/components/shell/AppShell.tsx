"use client";

import { AskPathFinder } from "@/components/ai/AskPathFinder";
import { JudgeGuide } from "@/components/judge/JudgeGuide";
import Link from "next/link";
import { useLayoutEffect, useRef, useState, type ReactNode } from "react";
import { usePathname, useRouter } from "next/navigation";
import { Button } from "@/components/ui/Button";
import { Mark } from "@/components/ui/Mark";
import { continueLabel, nextFlowView } from "@/lib/flow";
import { useIntelligence } from "@/lib/session";
import type { ViewId } from "@/lib/types";

const NAV: { id: ViewId; label: string }[] = [
  { id: "overview", label: "Overview" },
  { id: "path", label: "My Path" },
  { id: "prove", label: "Assessments" },
  { id: "map", label: "Skill Map" },
  { id: "history", label: "History" },
];

function isActive(id: ViewId, view: ViewId): boolean {
  if (id === "overview") return view === "overview" || view === "blockers";
  if (id === "path") return view === "path" || view === "changed" || view === "why";
  if (id === "prove") return view === "prove" || view === "assess" || view === "result";
  return id === view;
}

export function AppShell({ children, className }: { children: ReactNode; className?: string }) {
  const { view, setView, reset, attempt, roleName } = useIntelligence();
  const pathname = usePathname();
  const router = useRouter();
  const navRef = useRef<HTMLElement>(null);
  const [indicator, setIndicator] = useState({ x: 0, w: 0 });

  useLayoutEffect(() => {
    const nav = navRef.current;
    const active = nav?.querySelector<HTMLElement>("[data-active='true']");
    if (!nav || !active) return;
    const navBox = nav.getBoundingClientRect();
    const box = active.getBoundingClientRect();
    setIndicator({ x: box.left - navBox.left, w: box.width });
  }, [view]);

  function continueFlow() {
    if (view === "prove" || view === "assess") return;
    const next = nextFlowView(view);
    if (next) setView(next);
  }

  const continueNext = nextFlowView(view);
  const footerLabel = continueLabel(view);

  return (
    <div className={`min-h-screen ${className ?? ""}`.trim()}>
      <header className="app-header sticky top-0 z-20">
        <div className="mx-auto flex max-w-6xl items-center justify-between gap-6 px-6 py-3">
          <Link
            href="/"
            className="inline-flex items-center gap-2 text-[11px] font-medium tracking-[0.22em] text-paper transition-opacity hover:opacity-80"
          >
            <Mark className="h-3 w-[18px]" title="PathFinder" />
            PATHFINDER
          </Link>
          <nav ref={navRef} className="nav-track hidden items-center gap-1 pb-1 md:flex" aria-label="Primary">
            {NAV.map((item) => {
              const active = isActive(item.id, view);
              return (
                <button
                  key={item.id}
                  type="button"
                  data-active={active ? "true" : "false"}
                  onClick={() => setView(item.id === "overview" ? "overview" : item.id)}
                  className={`nav-link px-3 py-1.5 text-sm ${active ? "text-paper" : "text-mist hover:text-paper"}`}
                >
                  {item.label}
                </button>
              );
            })}
            <span
              className="nav-indicator"
              style={{ transform: `translateX(${indicator.x}px)`, width: indicator.w }}
            />
          </nav>
          <div className="flex items-center gap-3">
            <p className="type-meta hidden lg:block normal-case tracking-normal text-mist">{roleName}</p>
            <Button
              variant="ghost"
              onClick={() => {
                reset();
                router.push("/");
              }}
            >
              Reset
            </Button>
          </div>
        </div>
        <nav className="nav-mobile md:hidden" aria-label="Workspace">
          {NAV.map((item) => {
            const active = isActive(item.id, view);
            return (
              <button
                key={`m-${item.id}`}
                type="button"
                data-active={active ? "true" : "false"}
                onClick={() => setView(item.id === "overview" ? "overview" : item.id)}
                className={`nav-link ${active ? "text-paper" : "text-mist"}`}
              >
                {item.label}
              </button>
            );
          })}
        </nav>
      </header>
      <main className="mx-auto max-w-6xl px-6 py-10 pb-24">
        <JudgeGuide />
        {children}
        {view === "overview" || view === "path" || view === "changed" || view === "why" ? (
          <div className="mt-12">
            <AskPathFinder />
          </div>
        ) : null}
      </main>
      {pathname.startsWith("/workspace") &&
      view !== "assess" &&
      view !== "prove" &&
      view !== "result" &&
      view !== "changed" &&
      view !== "map" &&
      continueNext ? (
        <div className="sticky bottom-0 app-footer-bar border-t border-line bg-ink-950/95 backdrop-blur-sm">
          <div className="mx-auto flex max-w-6xl items-center justify-between px-6 py-3">
            <p className="type-meta normal-case tracking-[0.14em] text-mist">
              KNOW · DIAGNOSE · PROVE · ADAPT
              {attempt ? ` · ${attempt.adaptation}` : ""}
            </p>
            <Button onClick={continueFlow} showMark>
              {footerLabel}
            </Button>
          </div>
        </div>
      ) : null}
    </div>
  );
}

"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import type { ReactNode } from "react";
import { Button } from "@/components/ui/Button";
import { useIntelligence } from "@/lib/session";
import type { ViewId } from "@/lib/types";

const NAV: { id: ViewId; href: string; label: string }[] = [
  { id: "overview", href: "/workspace", label: "Overview" },
  { id: "path", href: "/workspace?view=path", label: "My Path" },
  { id: "prove", href: "/workspace?view=prove", label: "Assessments" },
  { id: "map", href: "/workspace?view=map", label: "Skill Map" },
  { id: "history", href: "/workspace?view=history", label: "History" },
];

const FLOW: ViewId[] = ["overview", "blockers", "path", "prove", "result", "changed", "why", "history"];

export function AppShell({ children }: { children: ReactNode }) {
  const { view, setView, reset, attempt, roleName } = useIntelligence();
  const pathname = usePathname();
  const router = useRouter();

  function continueFlow() {
    if (view === "prove") {
      setView("prove");
      return;
    }
    if (view === "assess") return;
    if (view === "result") {
      setView("changed");
      return;
    }
    const idx = FLOW.indexOf(view);
    const next = FLOW[Math.min(idx + 1, FLOW.length - 1)];
    setView(next);
  }

  const continueLabel =
    view === "result" ? "See what changed" : view === "prove" ? "Take assessment" : "Continue";

  return (
    <div className="min-h-screen">
      <header className="sticky top-0 z-20 border-b border-line bg-ink-950/90 backdrop-blur">
        <div className="mx-auto flex max-w-6xl items-center justify-between gap-6 px-6 py-3">
          <Link href="/" className="text-sm font-medium tracking-[0.14em] text-paper">
            PATHFINDER
          </Link>
          <nav className="hidden items-center gap-1 md:flex" aria-label="Primary">
            {NAV.map((item) => {
              const active =
                (item.id === "overview" && (view === "overview" || view === "blockers")) ||
                (item.id === "path" && (view === "path" || view === "changed" || view === "why")) ||
                (item.id === "prove" && (view === "prove" || view === "assess" || view === "result")) ||
                item.id === view;
              return (
                <button
                  key={item.id}
                  type="button"
                  onClick={() => setView(item.id === "overview" ? "overview" : item.id)}
                  className={`rounded-md px-3 py-1.5 text-sm ${
                    active ? "bg-ink-700 text-paper" : "text-mist hover:text-paper"
                  }`}
                >
                  {item.label}
                </button>
              );
            })}
          </nav>
          <div className="flex items-center gap-3">
            <p className="hidden text-xs text-mist lg:block">{roleName}</p>
            <Button variant="ghost" onClick={() => { reset(); router.push("/"); }}>
              Reset
            </Button>
          </div>
        </div>
      </header>
      <main className="mx-auto max-w-6xl px-6 py-8">{children}</main>
      {pathname.startsWith("/workspace") && view !== "assess" && view !== "prove" ? (
        <div className="sticky bottom-0 border-t border-line bg-ink-950/95">
          <div className="mx-auto flex max-w-6xl items-center justify-between px-6 py-3">
            <p className="text-xs text-mist">
              Diagnose → Prove → Adapt
              {attempt ? ` · last adaptation ${attempt.adaptation}` : ""}
            </p>
            <Button onClick={continueFlow}>{continueLabel}</Button>
          </div>
        </div>
      ) : null}
    </div>
  );
}

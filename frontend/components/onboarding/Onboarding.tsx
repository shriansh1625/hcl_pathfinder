"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { api } from "@/lib/api";
import { useIntelligence } from "@/lib/session";
import type { Role } from "@/lib/types";
import { Button } from "@/components/ui/Button";
import { ErrorState } from "@/components/ui/States";
import { Mark } from "@/components/ui/Mark";

const THESIS = [
  {
    n: "01",
    verb: "KNOW",
    line: "It knows what you know — from evidence, not guesses.",
  },
  {
    n: "02",
    verb: "DIAGNOSE",
    line: "It knows what the target career still requires.",
  },
  {
    n: "03",
    verb: "ADAPT",
    line: "It changes the path when new evidence changes the diagnosis.",
  },
] as const;

const STYLE_LABEL: Record<string, string> = {
  MIXED: "Mixed",
  HANDS_ON: "Hands-on",
  READING: "Reading",
  VIDEO: "Video",
  PROJECT: "Project",
};

export function Onboarding() {
  const router = useRouter();
  const { launchDemo, launchJudgeDemo, startCustom, mutating, error, learnerId } = useIntelligence();
  const [roles, setRoles] = useState<Role[]>([]);
  const [role, setRole] = useState("ai-ml-engineer");
  const [hours, setHours] = useState(8);
  const [style, setStyle] = useState("MIXED");
  const [loadError, setLoadError] = useState<string | null>(null);

  useEffect(() => {
    api
      .roles()
      .then((items) => {
        setRoles(items);
        if (items.some((item) => item.slug === "ai-ml-engineer")) {
          setRole("ai-ml-engineer");
        }
      })
      .catch((err: Error) => setLoadError(err.message));
  }, []);

  useEffect(() => {
    if (learnerId) router.replace("/workspace");
  }, [learnerId, router]);

  const options = roles.length ? roles : [{ slug: "ai-ml-engineer", name: "AI/ML Engineer" }];
  const selected = options.find((item) => item.slug === role);

  async function onJudgeDemo() {
    await launchJudgeDemo({ role, weeklyHours: hours, learningStyle: style });
    router.push("/workspace");
  }

  async function onDemo() {
    await launchDemo({ role, weeklyHours: hours, learningStyle: style });
    router.push("/workspace");
  }

  async function onCustom() {
    await startCustom({
      role,
      roleName: selected?.name ?? role,
      weeklyHours: hours,
      learningStyle: style,
      withDemoEvidence: true,
    });
    router.push("/workspace");
  }

  return (
    <div className="mx-auto grid min-h-screen max-w-6xl items-center gap-16 px-6 py-16 onboard-shell lg:grid-cols-[1.15fr_0.85fr]">
      <div>
        <p className="flex items-center gap-2.5 text-[11px] font-medium uppercase tracking-[0.22em] text-mist">
          <Mark className="h-3.5 w-5 text-paper" title="PathFinder" />
          PathFinder
        </p>
        <h1 className="mt-5 max-w-xl font-display text-5xl font-medium leading-[1.12] text-paper">
          Build the path to the career you actually want.
        </h1>
        <p className="mt-5 max-w-lg text-base leading-relaxed text-mist">
          PathFinder diagnoses your current competency, identifies what is blocking your target
          role, and adapts your roadmap as you prove new skills.
        </p>
        <ul className="mt-10 space-y-1">
          {THESIS.map((item) => (
            <li key={item.verb}>
              <button type="button" className="thesis-row w-full text-left">
                <span className="thesis-index">{item.n}</span>
                <span className="thesis-verb">{item.verb}</span>
                <span className="thesis-line">{item.line}</span>
              </button>
            </li>
          ))}
        </ul>
      </div>

      <div className="border-y border-line py-8">
        {loadError ? <div className="mb-4"><ErrorState message={loadError} /></div> : null}
        {error ? <div className="mb-4"><ErrorState message={error} /></div> : null}

        <p className="text-[11px] uppercase tracking-[0.2em] text-mist">Your destination</p>
        <label className="sr-only" htmlFor="target-career">Target career</label>
        <div className="relative mt-3">
          <select
            id="target-career"
            className="field-destination w-full pr-8 font-display text-3xl font-medium text-paper"
            value={role}
            onChange={(event) => setRole(event.target.value)}
          >
            {options.map((item) => (
              <option key={item.slug} value={item.slug}>
                {item.name}
              </option>
            ))}
          </select>
          <Mark className="pointer-events-none absolute right-0 top-[0.85rem] h-3 w-[18px] text-paper/45" />
        </div>

        <div className="mt-6 flex flex-wrap items-baseline gap-x-3 gap-y-2 font-mono text-xs uppercase tracking-[0.14em] text-mist">
          <label className="inline-flex items-baseline gap-2">
            <input
              type="number"
              min={2}
              max={40}
              value={hours}
              onChange={(event) => setHours(Number(event.target.value))}
              className="field-inline w-10 text-paper"
            />
            hours / week
          </label>
          <span aria-hidden>·</span>
          <label>
            <span className="sr-only">Learning preference</span>
            <select
              className="field-inline text-mist"
              value={style}
              onChange={(event) => setStyle(event.target.value)}
            >
              {Object.entries(STYLE_LABEL).map(([value, label]) => (
                <option key={value} value={value}>
                  {label}
                </option>
              ))}
            </select>
          </label>
        </div>

        <p className="mt-8 text-xs leading-relaxed text-mist">
          Evidence is taken from the live backend. Missing evidence stays UNKNOWN — never 0%.
        </p>

        <div className="mt-8 space-y-3">
          <Button className="cta-go w-full justify-between py-3.5" disabled={mutating} onClick={() => void onDemo()}>
            <span>{mutating ? "Diagnosing…" : "Build my path"}</span>
            <span className="mark-arrow inline-flex" aria-hidden>
              <Mark className="h-3 w-[18px]" />
            </span>
          </Button>
          <Button variant="ghost" className="w-full" disabled={mutating} onClick={() => void onJudgeDemo()}>
            Judge demo (~90s)
          </Button>
          <Button variant="ghost" className="w-full" disabled={mutating} onClick={() => void onCustom()}>
            Use demo evidence
          </Button>
        </div>
      </div>
    </div>
  );
}

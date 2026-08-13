"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { api } from "@/lib/api";
import { useIntelligence } from "@/lib/session";
import type { Role } from "@/lib/types";
import { Button } from "@/components/ui/Button";
import { ErrorState } from "@/components/ui/States";

export function Onboarding() {
  const router = useRouter();
  const { launchDemo, startCustom, mutating, error, learnerId } = useIntelligence();
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

  const selected = roles.find((item) => item.slug === role);

  async function onDemo() {
    await launchDemo({ role, weeklyHours: hours, learningStyle: style });
    router.push("/workspace");
  }

  async function onCustom(withEvidence: boolean) {
    await startCustom({
      role,
      roleName: selected?.name ?? role,
      weeklyHours: hours,
      learningStyle: style,
      withDemoEvidence: withEvidence,
    });
    router.push("/workspace");
  }

  return (
    <div className="mx-auto grid min-h-screen max-w-6xl items-center gap-12 px-6 py-16 lg:grid-cols-[1.1fr_0.9fr]">
      <div>
        <p className="text-[11px] font-medium uppercase tracking-[0.22em] text-accent">PathFinder</p>
        <h1 className="mt-4 max-w-xl text-4xl font-medium leading-tight text-paper sm:text-5xl">
          Build the path to the career you actually want.
        </h1>
        <p className="mt-5 max-w-lg text-base leading-relaxed text-mist">
          PathFinder diagnoses your current competency, identifies what is blocking your target
          role, and adapts your roadmap as you prove new skills.
        </p>
        <ul className="mt-8 space-y-3 text-sm text-mist">
          <li>It knows what you know — from evidence, not guesses.</li>
          <li>It knows what the target career still requires.</li>
          <li>It changes the path when new evidence changes the diagnosis.</li>
        </ul>
      </div>

      <div className="rounded-2xl border border-line bg-ink-800 p-6 shadow-panel">
        <p className="text-[11px] uppercase tracking-[0.18em] text-mist">Goal</p>
        <h2 className="mt-1 text-xl text-paper">Set the career target</h2>

        {loadError ? <div className="mt-4"><ErrorState message={loadError} /></div> : null}
        {error ? <div className="mt-4"><ErrorState message={error} /></div> : null}

        <label className="mt-6 block text-xs uppercase tracking-wider text-mist">Target career</label>
        <select
          className="mt-2 w-full rounded-md border border-line bg-ink-900 px-3 py-2 text-sm text-paper"
          value={role}
          onChange={(event) => setRole(event.target.value)}
        >
          {(roles.length
            ? roles
            : [{ slug: "ai-ml-engineer", name: "AI/ML Engineer" }]
          ).map((item) => (
            <option key={item.slug} value={item.slug}>
              {item.name}
            </option>
          ))}
        </select>

        <label className="mt-4 block text-xs uppercase tracking-wider text-mist">Weekly learning time</label>
        <input
          type="number"
          min={2}
          max={40}
          value={hours}
          onChange={(event) => setHours(Number(event.target.value))}
          className="mt-2 w-full rounded-md border border-line bg-ink-900 px-3 py-2 text-sm text-paper"
        />

        <label className="mt-4 block text-xs uppercase tracking-wider text-mist">Learning preference</label>
        <select
          className="mt-2 w-full rounded-md border border-line bg-ink-900 px-3 py-2 text-sm text-paper"
          value={style}
          onChange={(event) => setStyle(event.target.value)}
        >
          <option value="MIXED">Mixed</option>
          <option value="HANDS_ON">Hands-on</option>
          <option value="READING">Reading</option>
          <option value="VIDEO">Video</option>
          <option value="PROJECT">Project</option>
        </select>

        <p className="mt-4 text-xs text-mist">
          Evidence input: the live demo seeds verified backend evidence for the AI/ML Engineer
          scenario. PathFinder never treats missing evidence as 0%.
        </p>

        <div className="mt-6 space-y-3">
          <Button className="w-full py-3" disabled={mutating} onClick={() => void onDemo()}>
            {mutating ? "Diagnosing…" : "Launch Live Demo"}
          </Button>
          <Button
            variant="secondary"
            className="w-full"
            disabled={mutating}
            onClick={() => void onCustom(true)}
          >
            Use Demo Learner
          </Button>
        </div>
        <p className="mt-3 text-center text-[11px] text-mist">
          Live backend. No hardcoded frontend state.
        </p>
      </div>
    </div>
  );
}

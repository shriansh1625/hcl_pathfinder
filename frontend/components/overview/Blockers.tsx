"use client";

import { StatusBadge } from "@/components/ui/StatusBadge";
import { Panel } from "@/components/ui/Panel";
import { Button } from "@/components/ui/Button";
import { useIntelligence } from "@/lib/session";
import { prettySkill, proficiencyLabel, visualState } from "@/lib/status";

export function Blockers() {
  const { gaps, setView } = useIntelligence();
  const blockers = [...gaps]
    .filter((item) => item.attainment !== "TARGET_MET")
    .sort((a, b) => b.action_priority - a.action_priority)
    .slice(0, 5);

  return (
    <div className="space-y-6">
      <div>
        <p className="text-[11px] uppercase tracking-[0.2em] text-accent">Diagnosis</p>
        <h1 className="mt-2 text-3xl font-medium text-paper">Your biggest career blockers</h1>
        <p className="mt-2 max-w-2xl text-sm text-mist">
          Not all gaps are equal. A smaller foundational gap can matter more than a larger isolated
          one. Priority and downstream impact come from the backend — they are not recalculated here.
        </p>
      </div>

      <div className="grid gap-4 lg:grid-cols-2">
        {blockers.map((item) => (
          <Panel key={item.skill} className="p-5">
            <div className="flex items-start justify-between gap-3">
              <div>
                <h2 className="text-lg text-paper">{item.name || prettySkill(item.skill)}</h2>
                <p className="mt-1 font-mono text-sm text-mist">
                  {proficiencyLabel(item)}
                  {item.evidence_state !== "UNKNOWN" ? ` → ${item.target_level.toFixed(2)}` : ""}
                </p>
              </div>
              <StatusBadge state={visualState(item)} />
            </div>
            <p className="mt-4 text-xs uppercase tracking-wider text-mist">Action</p>
            <p className="text-sm text-paper">{item.action}</p>
            <p className="mt-3 text-xs uppercase tracking-wider text-mist">
              {item.action === "VERIFY" ? "Blocks" : "Impacts"}
            </p>
            <p className="text-sm text-paper">
              {(item.hard_downstream.slice(0, 4).map(prettySkill).join(", ") || "—")}
            </p>
            {item.blockers.length ? (
              <p className="mt-3 text-xs text-mist">
                Waiting on: {item.blockers.map(prettySkill).join(", ")}
              </p>
            ) : null}
            <p className="mt-4 text-xs leading-relaxed text-mist">{item.explanation}</p>
          </Panel>
        ))}
      </div>

      <div className="flex justify-end">
        <Button onClick={() => setView("path")}>Continue</Button>
      </div>
    </div>
  );
}

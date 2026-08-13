"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { AppShell } from "@/components/shell/AppShell";
import { Overview } from "@/components/overview/Overview";
import { Blockers } from "@/components/overview/Blockers";
import { PathView } from "@/components/path/PathView";
import { PathChanged } from "@/components/path/PathChanged";
import { ProveIt } from "@/components/assess/ProveIt";
import { AssessmentRun } from "@/components/assess/AssessmentRun";
import { ResultView } from "@/components/assess/ResultView";
import { WhyChanged } from "@/components/assess/WhyChanged";
import { TimelineView } from "@/components/history/TimelineView";
import { SkillMap } from "@/components/map/SkillMap";
import { ErrorState, LoadingState } from "@/components/ui/States";
import { useIntelligence } from "@/lib/session";

export default function WorkspacePage() {
  const { learnerId, hydrated, view, error, refresh } = useIntelligence();
  const router = useRouter();

  useEffect(() => {
    if (hydrated && !learnerId) {
      router.replace("/");
    }
  }, [hydrated, learnerId, router]);

  if (!hydrated || !learnerId) {
    return (
      <div className="flex min-h-screen items-center justify-center">
        <LoadingState label="Restoring session…" />
      </div>
    );
  }

  return (
    <AppShell>
      {error ? <div className="mb-6"><ErrorState message={error} onRetry={() => void refresh()} /></div> : null}
      {view === "overview" ? <Overview /> : null}
      {view === "blockers" ? <Blockers /> : null}
      {view === "path" ? <PathView /> : null}
      {view === "prove" ? <ProveIt /> : null}
      {view === "assess" ? <AssessmentRun /> : null}
      {view === "result" ? <ResultView /> : null}
      {view === "changed" ? <PathChanged /> : null}
      {view === "why" ? <WhyChanged /> : null}
      {view === "history" ? <TimelineView /> : null}
      {view === "map" ? <SkillMap /> : null}
    </AppShell>
  );
}

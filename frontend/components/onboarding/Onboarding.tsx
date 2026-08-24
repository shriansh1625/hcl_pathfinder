"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { api, ApiError } from "@/lib/api";
import { useIntelligence } from "@/lib/session";
import type { GoalIntake, Role } from "@/lib/types";
import { Button } from "@/components/ui/Button";
import { LoadingState } from "@/components/ui/States";
import { Mark } from "@/components/ui/Mark";
import { AmbientPathGraph } from "@/components/onboarding/AmbientPathGraph";
import { CareerExplorer } from "@/components/onboarding/CareerExplorer";
import { GoalIntelligenceField } from "@/components/onboarding/GoalIntelligenceField";
import { OnboardStepPanel } from "@/components/onboarding/OnboardStepPanel";
import { OnboardStepRail } from "@/components/onboarding/OnboardStepRail";
import { OnboardAlert } from "@/components/onboarding/OnboardAlert";
import { prettySkill } from "@/lib/status";

const THESIS = [
  { n: "01", verb: "KNOW", line: "It knows what you know — from evidence, not guesses." },
  { n: "02", verb: "DIAGNOSE", line: "It knows what the target career still requires." },
  { n: "03", verb: "ADAPT", line: "It changes the path when new evidence changes the diagnosis." },
] as const;

const STYLE_LABEL: Record<string, string> = {
  MIXED: "Mixed",
  HANDS_ON: "Hands-on",
  READING: "Reading",
  VIDEO: "Video",
  PROJECT: "Project",
};

const EXPERIENCE = [
  { value: "BEGINNER", label: "Beginner", detail: "Starting out" },
  { value: "INTERMEDIATE", label: "Intermediate", detail: "Some professional experience" },
  { value: "ADVANCED", label: "Advanced", detail: "Strong track record" },
];

const INTEREST_SUGGESTIONS = ["cloud security", "computer vision", "APIs", "MLOps", "data pipelines"];

function thesisActiveIndex(step: number): number {
  if (step === 0) return 0;
  if (step >= 6) return 2;
  return 1;
}

function intakeErrorMessage(err: unknown): string {
  if (err instanceof ApiError) {
    if (err.status === 404) {
      return "Goal intake API not found (/v1/intake/goal). Restart the backend or use “Pick career manually”.";
    }
    return typeof err.detail === "string" ? err.detail : err.message;
  }
  return err instanceof Error ? err.message : "Could not interpret goal";
}

export function Onboarding() {
  const router = useRouter();
  const { launchDemo, launchJudgeDemo, startCustom, mutating, error, learnerId } = useIntelligence();
  const [roles, setRoles] = useState<Role[]>([]);
  const [step, setStep] = useState(0);
  const [goalText, setGoalText] = useState("");
  const [intake, setIntake] = useState<GoalIntake | null>(null);
  const [intakeLoading, setIntakeLoading] = useState(false);
  const [role, setRole] = useState("");
  const [careerQuery, setCareerQuery] = useState("");
  const [experience, setExperience] = useState("BEGINNER");
  const [interests, setInterests] = useState("");
  const [hours, setHours] = useState(8);
  const [style, setStyle] = useState("MIXED");
  const [withDemoEvidence, setWithDemoEvidence] = useState(true);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [launching, setLaunching] = useState(false);
  const [headlineReady, setHeadlineReady] = useState(false);

  useEffect(() => {
    api
      .roles()
      .then((items) => {
        setRoles(items);
        if (!role && items.length) setRole(items[0].slug);
      })
      .catch((err: Error) => setLoadError(err.message));
  }, [role]);

  useEffect(() => {
    if (learnerId) router.replace("/workspace");
  }, [learnerId, router]);

  useEffect(() => {
    const t = window.setTimeout(() => setHeadlineReady(true), 40);
    return () => window.clearTimeout(t);
  }, []);

  const selected = roles.find((item) => item.slug === role);
  const busy = mutating || launching || intakeLoading;
  const activeThesis = thesisActiveIndex(step);

  async function resolveGoal(): Promise<GoalIntake> {
    setIntakeLoading(true);
    setLoadError(null);
    try {
      const result = await api.interpretGoal(goalText.trim());
      setIntake(result);
      if (result.role?.slug) setRole(result.role.slug);
      if (result.weekly_hours) setHours(Math.round(result.weekly_hours));
      if (result.learning_style) setStyle(result.learning_style);
      return result;
    } catch (err) {
      setLoadError(intakeErrorMessage(err));
      throw err;
    } finally {
      setIntakeLoading(false);
    }
  }

  async function runLaunch(action: () => Promise<void>) {
    setLaunching(true);
    try {
      await action();
      await new Promise((r) => window.setTimeout(r, 520));
      sessionStorage.setItem("pf-workspace-arrival", "1");
      router.push("/workspace");
    } finally {
      setLaunching(false);
    }
  }

  const profileOpts = {
    role,
    roleName: selected?.name ?? role,
    weeklyHours: hours,
    learningStyle: style,
    withDemoEvidence,
    experienceLevel: experience,
    interests: interests
      .split(",")
      .map((item) => item.trim())
      .filter(Boolean),
    goalText: goalText.trim() || intake?.goal_text || "",
    intakeSkills: intake?.skills.map((item) => ({
      skill: item.skill,
      observed_level: item.observed_level,
    })),
  };

  return (
    <div
      className={`mx-auto grid min-h-screen max-w-6xl items-start gap-16 px-6 py-16 onboard-shell lg:grid-cols-[1.15fr_0.85fr] ${launching ? "onboard-launching" : ""}`}
    >
      <div className="onboard-hero relative">
        <AmbientPathGraph step={step} resolved={Boolean(intake?.role)} launching={launching} />
        <p className="onboard-reveal type-section flex items-center gap-2.5" style={{ animationDelay: "0ms" }}>
          <Mark className="h-3.5 w-5 text-paper" title="PathFinder" />
          PathFinder
        </p>
        <h1
          className={`type-display onboard-headline mt-5 max-w-xl text-5xl font-medium text-paper ${headlineReady ? "is-ready" : ""}`}
        >
          Build the path to the career you actually want.
        </h1>
        <p className="onboard-reveal mt-5 max-w-lg text-base leading-relaxed text-mist" style={{ animationDelay: "120ms" }}>
          Describe your goal in your own words. PathFinder resolves it against a fixed career ontology —
          never inventing roles, skills, or prerequisites.
        </p>
        <ul className="mt-10 space-y-1">
          {THESIS.map((item, index) => (
            <li key={item.verb}>
              <button
                type="button"
                className={`thesis-row w-full text-left ${activeThesis === index ? "is-active" : ""}`}
              >
                <span className="thesis-index">{item.n}</span>
                <span className="thesis-verb">
                  <span className="thesis-waypoint" aria-hidden />
                  {item.verb}
                </span>
                <span className="thesis-line">{item.line}</span>
              </button>
            </li>
          ))}
        </ul>
        <div className="onboard-reveal mt-10 hidden lg:block" style={{ animationDelay: "280ms" }}>
          <p className="type-section">Why PathFinder is different</p>
          <ul className="mt-3 space-y-2 text-sm text-mist">
            <li>UNKNOWN means missing evidence — not failure or 0%.</li>
            <li>Gaps are dependency-aware, not keyword matches.</li>
            <li>Semantic ML is bounded; the LLM explains but cannot change the path.</li>
          </ul>
        </div>
      </div>

      <div className="onboard-destination">
        <Mark className="onboard-destination-mark absolute right-6 top-6 h-3 w-[18px] text-accent/60" aria-hidden />
        <OnboardStepRail step={step} />

        {(loadError || error) ? (
          <OnboardAlert
            message={loadError ?? error ?? "Request failed"}
            onDismiss={loadError ? () => setLoadError(null) : undefined}
            onRetry={step === 0 && loadError ? () => void resolveGoal() : undefined}
          />
        ) : null}

        <div className="onboard-panel-body">
          <OnboardStepPanel step={step}>
            {step === 0 ? (
              <GoalIntelligenceField
                goalText={goalText}
                onGoalTextChange={setGoalText}
                busy={busy}
                resolvedIntake={intake}
                onResolve={resolveGoal}
                onManual={() => setStep(1)}
                onContinueFromResolution={() => setStep(1)}
              />
            ) : null}

            {step === 1 ? (
              <div>
                <p className="type-section">Target career</p>
                {intake?.role ? (
                  <p className="mt-2 text-sm text-mist">
                    Inferred: <span className="text-paper">{intake.role.name}</span>
                    {intake.unresolved.length ? ` · Unresolved: ${intake.unresolved.join(", ")}` : ""}
                  </p>
                ) : null}
                <div className="mt-4">
                  <CareerExplorer
                    roles={roles}
                    selected={role}
                    onSelect={setRole}
                    query={careerQuery}
                    onQueryChange={setCareerQuery}
                    learnerId={learnerId}
                    onLoadError={setLoadError}
                  />
                </div>
                <div className="mt-4 flex gap-2">
                  <Button variant="ghost" onClick={() => setStep(0)}>
                    Back
                  </Button>
                  <Button disabled={!role} onClick={() => setStep(2)}>
                    Continue
                  </Button>
                </div>
              </div>
            ) : null}

            {step === 2 ? (
              <div>
                <p className="type-section">Current experience</p>
                <div className="mt-4 grid gap-2">
                  {EXPERIENCE.map((item) => (
                    <button
                      key={item.value}
                      type="button"
                      className={`experience-card ${experience === item.value ? "is-selected" : ""}`}
                      onClick={() => setExperience(item.value)}
                    >
                      <span className="experience-card-label">{item.label}</span>
                      <span className="experience-card-detail">{item.detail}</span>
                    </button>
                  ))}
                </div>
                <div className="mt-4 flex gap-2">
                  <Button variant="ghost" onClick={() => setStep(1)}>
                    Back
                  </Button>
                  <Button onClick={() => setStep(3)}>Continue</Button>
                </div>
              </div>
            ) : null}

            {step === 3 ? (
              <div>
                <p className="type-section">Interests & specialization</p>
                <input
                  className="field-inline mt-4 w-full text-paper"
                  placeholder="computer vision, cloud security, APIs…"
                  value={interests}
                  onChange={(event) => setInterests(event.target.value)}
                />
                <div className="mt-3 flex flex-wrap gap-2">
                  {INTEREST_SUGGESTIONS.map((chip) => (
                    <button
                      key={chip}
                      type="button"
                      className="interest-chip"
                      onClick={() =>
                        setInterests((current) =>
                          current.includes(chip) ? current : current ? `${current}, ${chip}` : chip,
                        )
                      }
                    >
                      {chip}
                    </button>
                  ))}
                </div>
                <div className="mt-4 flex gap-2">
                  <Button variant="ghost" onClick={() => setStep(2)}>
                    Back
                  </Button>
                  <Button onClick={() => setStep(4)}>Continue</Button>
                </div>
              </div>
            ) : null}

            {step === 4 ? (
              <div>
                <p className="type-section">Time & learning preference</p>
                <div className="schedule-control mt-4">
                  <label className="schedule-field">
                    <span className="schedule-label">Hours / week</span>
                    <input
                      type="number"
                      min={2}
                      max={40}
                      value={hours}
                      onChange={(event) => setHours(Number(event.target.value))}
                      className="schedule-input"
                    />
                  </label>
                  <label className="schedule-field">
                    <span className="schedule-label">Style</span>
                    <select className="schedule-select" value={style} onChange={(event) => setStyle(event.target.value)}>
                      {Object.entries(STYLE_LABEL).map(([value, label]) => (
                        <option key={value} value={value}>
                          {label}
                        </option>
                      ))}
                    </select>
                  </label>
                </div>
                <div className="mt-4 flex gap-2">
                  <Button variant="ghost" onClick={() => setStep(3)}>
                    Back
                  </Button>
                  <Button onClick={() => setStep(5)}>Continue</Button>
                </div>
              </div>
            ) : null}

            {step === 5 ? (
              <div>
                <p className="type-section">What PathFinder knows</p>
                <p className="mt-2 text-sm text-mist">
                  Role-specific demo evidence seeds your competency model. Without it, gaps remain UNKNOWN.
                </p>
                <label className="evidence-toggle mt-4">
                  <input
                    type="checkbox"
                    checked={withDemoEvidence}
                    onChange={(event) => setWithDemoEvidence(event.target.checked)}
                  />
                  <span>Load demo evidence for {selected?.name ?? "this role"}</span>
                </label>
                {intake?.skills.length ? (
                  <div className="evidence-from-goal mt-4">
                    <p className="type-section">From your goal</p>
                    <ul className="mt-2 space-y-1 text-xs text-mist">
                      {intake.skills.map((item) => (
                        <li key={item.skill} className="flex justify-between gap-4">
                          <span className="text-paper">{item.name}</span>
                          <span className="font-mono tabular-nums">{item.observed_level.toFixed(2)}</span>
                        </li>
                      ))}
                    </ul>
                  </div>
                ) : (
                  <p className="mt-4 text-xs text-mist">No goal claims yet — evidence will start as UNKNOWN.</p>
                )}
                <div className="mt-4 flex gap-2">
                  <Button variant="ghost" onClick={() => setStep(4)}>
                    Back
                  </Button>
                  <Button onClick={() => setStep(6)}>Review profile</Button>
                </div>
              </div>
            ) : null}

            {step === 6 ? (
              <div className="path-config-summary">
                <p className="type-section">Your path configuration</p>
                <dl className="path-config-grid mt-4">
                  <div>
                    <dt>Destination</dt>
                    <dd>{selected?.name}</dd>
                  </div>
                  <div>
                    <dt>Experience</dt>
                    <dd>{EXPERIENCE.find((item) => item.value === experience)?.label}</dd>
                  </div>
                  <div>
                    <dt>Interests</dt>
                    <dd>{interests || "—"}</dd>
                  </div>
                  <div>
                    <dt>Time</dt>
                    <dd>
                      {hours} hours / week
                    </dd>
                  </div>
                  <div>
                    <dt>Learning style</dt>
                    <dd>{STYLE_LABEL[style] ?? style}</dd>
                  </div>
                  <div>
                    <dt>Evidence</dt>
                    <dd>{withDemoEvidence ? "Verified + self-reported" : "Self-reported only"}</dd>
                  </div>
                </dl>
                <div className="mt-8 space-y-3">
                  <Button
                    className="cta-go w-full justify-between py-3.5"
                    disabled={busy}
                    showMark
                    onClick={() => void runLaunch(() => startCustom(profileOpts))}
                  >
                    <span>{busy ? "Building your path…" : "Build my path"}</span>
                    <Mark className="mark-arrow inline-flex h-3 w-[18px]" aria-hidden />
                  </Button>
                  <Button variant="ghost" className="w-full" disabled={busy} onClick={() => void runLaunch(() => launchDemo(profileOpts))}>
                    Quick demo launch
                  </Button>
                  <Button variant="ghost" className="w-full" disabled={busy} onClick={() => void runLaunch(() => launchJudgeDemo(profileOpts))}>
                    Judge demo (~90s)
                  </Button>
                </div>
                <Button variant="ghost" className="mt-3 w-full" onClick={() => setStep(5)}>
                  Back
                </Button>
              </div>
            ) : null}
          </OnboardStepPanel>
        </div>

        {busy && !(step === 0 && intakeLoading) ? (
          <div className="onboard-inline-status" aria-live="polite">
            <LoadingState label={launching ? "Building your path" : "Preparing your career intelligence"} />
          </div>
        ) : null}
      </div>
    </div>
  );
}

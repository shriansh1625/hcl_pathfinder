"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { api, ApiError } from "@/lib/api";
import { useIntelligence } from "@/lib/session";
import type { GoalIntake, Role } from "@/lib/types";
import { Button } from "@/components/ui/Button";
import { LoadingState } from "@/components/ui/States";
import { CareerExplorer } from "@/components/onboarding/CareerExplorer";
import { GoalIntelligenceField } from "@/components/onboarding/GoalIntelligenceField";
import { OnboardStepPanel } from "@/components/onboarding/OnboardStepPanel";
import { OnboardStepRail } from "@/components/onboarding/OnboardStepRail";
import { OnboardAlert } from "@/components/onboarding/OnboardAlert";
import { prettySkill } from "@/lib/status";

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

function intakeErrorMessage(err: unknown): string {
  if (err instanceof ApiError) {
    if (err.status === 404) {
      return "Goal service unavailable. Restart the backend or use “Pick career manually”.";
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
  const [rolesError, setRolesError] = useState<string | null>(null);
  const [rolesLoading, setRolesLoading] = useState(true);
  const [launching, setLaunching] = useState(false);

  async function loadRoles() {
    setRolesLoading(true);
    setRolesError(null);
    try {
      const items = await api.roles();
      setRoles(items);
      setRole((current) => current || items[0]?.slug || "");
      return items;
    } catch (err) {
      const message = err instanceof Error ? err.message : "Could not load careers";
      setRolesError(message);
      return [];
    } finally {
      setRolesLoading(false);
    }
  }

  useEffect(() => {
    void loadRoles().catch(() => undefined);
  }, []);

  useEffect(() => {
    if (step === 1 && !roles.length) {
      void loadRoles().catch(() => undefined);
    }
  }, [step, roles.length]);

  useEffect(() => {
    if (learnerId) router.replace("/workspace");
  }, [learnerId, router]);

  const selected = roles.find((item) => item.slug === role);
  const goalBusy = intakeLoading || launching;
  const wizardBusy = mutating || launching;

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
    <div className={`onboard-wizard ${launching ? "onboard-launching" : ""}`}>
      <div className="onboard-destination onboard-destination-standalone">
        <OnboardStepRail step={step} />

        {(loadError || (step > 0 && (rolesError || error))) ? (
          <OnboardAlert
            message={loadError ?? rolesError ?? error ?? "Request failed"}
            onDismiss={loadError || rolesError ? () => {
              setLoadError(null);
              setRolesError(null);
            } : undefined}
            onRetry={
              step === 0 && loadError
                ? () => void resolveGoal()
                : rolesError
                  ? () => void loadRoles()
                  : undefined
            }
            onManual={
              step === 0 && loadError
                ? () => {
                    setLoadError(null);
                    setStep(1);
                  }
                : undefined
            }
          />
        ) : null}

        <div className="onboard-panel-body">
          <OnboardStepPanel step={step}>
            {step === 0 ? (
              <GoalIntelligenceField
                goalText={goalText}
                onGoalTextChange={setGoalText}
                busy={goalBusy}
                resolvedIntake={intake}
                onResolve={resolveGoal}
                onManual={() => {
                  setLoadError(null);
                  setStep(1);
                }}
                onContinueFromResolution={() => setStep(1)}
                onSelectAmbiguousRole={(slug) => {
                  setRole(slug);
                  setStep(1);
                }}
                onSeeSupportedCareers={() => setStep(1)}
              />
            ) : null}

            {step === 1 ? (
              <div>
                <p className="type-section">Choose your destination career</p>
                {intake?.role ? (
                  <p className="mt-2 text-sm text-mist">
                    Suggested: <span className="text-paper">{intake.role.name}</span>
                    {intake.unresolved.length ? ` · Also mentioned: ${intake.unresolved.join(", ")}` : ""}
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
                <p className="type-section">Where are you starting from?</p>
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
                <p className="type-section">What interests you most?</p>
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
                <p className="type-section">How do you like to learn?</p>
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
                <p className="type-section">Your starting evidence</p>
                <p className="mt-2 text-sm text-mist">
                  Demo evidence seeds your profile so you can see a realistic path. Without it, skills start as “not yet proven.”
                </p>
                <label className="evidence-toggle mt-4">
                  <input
                    type="checkbox"
                    checked={withDemoEvidence}
                    onChange={(event) => setWithDemoEvidence(event.target.checked)}
                  />
                  <span>Load sample evidence for {selected?.name ?? "this role"}</span>
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
                  <p className="mt-4 text-xs text-mist">No skills mentioned yet — we will start from an honest baseline.</p>
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
                <p className="type-section">Ready to build your path</p>
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
                    <dd>{withDemoEvidence ? "Sample + self-reported" : "Self-reported only"}</dd>
                  </div>
                </dl>
                <div className="path-config-actions mt-8">
                  <Button
                    className="cta-go w-full justify-center gap-2.5 py-3.5"
                    disabled={wizardBusy}
                    showMark
                    onClick={() => void runLaunch(() => startCustom(profileOpts))}
                  >
                    <span>{wizardBusy ? "Building your path…" : "Build my path"}</span>
                  </Button>
                  <Button variant="ghost" className="mt-3 w-full justify-center" disabled={wizardBusy} onClick={() => void runLaunch(() => launchDemo(profileOpts))}>
                    Quick demo launch
                  </Button>
                  <Button variant="ghost" className="mt-3 w-full justify-center" disabled={wizardBusy} onClick={() => void runLaunch(() => launchJudgeDemo(profileOpts))}>
                    Judge demo (~90s)
                  </Button>
                  <Button variant="ghost" className="mt-3 w-full justify-center" onClick={() => setStep(5)}>
                    Back
                  </Button>
                </div>
              </div>
            ) : null}
          </OnboardStepPanel>
        </div>

        {wizardBusy && !(step === 0 && intakeLoading) ? (
          <div className="onboard-inline-status" aria-live="polite">
            <LoadingState label={launching ? "Building your path" : "Preparing your profile"} />
          </div>
        ) : null}
      </div>
    </div>
  );
}

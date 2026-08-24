"use client";

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from "react";
import { api, ApiError } from "./api";
import type {
  AssessmentAttempt,
  AssessmentPublic,
  Dashboard,
  EvidenceRow,
  FusedSkill,
  GapItem,
  GapSnapshot,
  PathDiff,
  PathRead,
  ProgressFeedback,
  ProgressOutcome,
  SuggestedAssessment,
  TimelineEntry,
  ViewId,
} from "./types";

const STORAGE_KEY = "pathfinder.session.v1";
const JUDGE_KEY = "pathfinder.judge.v1";

export type SessionSnapshot = {
  learnerId: string;
  displayName: string;
  role: string;
  roleName: string;
  weeklyHours: number;
  learningStyle: string;
  v1PathId: string | null;
  view: ViewId;
};

type IntelligenceContext = {
  learnerId: string | null;
  hydrated: boolean;
  displayName: string;
  role: string;
  roleName: string;
  weeklyHours: number;
  learningStyle: string;
  view: ViewId;
  gaps: GapItem[];
  dashboard: Dashboard | null;
  paths: PathRead[];
  activePath: PathRead | null;
  previousPath: PathRead | null;
  timeline: TimelineEntry[];
  suggested: SuggestedAssessment | null;
  assessment: AssessmentPublic | null;
  attempt: AssessmentAttempt | null;
  diff: PathDiff | null;
  beforeGaps: GapSnapshot[];
  skills: FusedSkill[];
  judgeMode: boolean;
  loading: boolean;
  mutating: boolean;
  error: string | null;
  updatingModel: boolean;
  setView: (view: ViewId) => void;
  refresh: () => Promise<void>;
  launchDemo: (opts?: LaunchOpts) => Promise<void>;
  launchJudgeDemo: (opts?: LaunchOpts) => Promise<void>;
  startCustom: (opts: LaunchOpts) => Promise<void>;
  completeFirstExecutable: () => Promise<void>;
  loadAssessment: (slug: string) => Promise<void>;
  submitAnswers: (answers: number[]) => Promise<void>;
  loadEvidence: (skill: string) => Promise<EvidenceRow[]>;
  recordProgress: (
    pathId: string,
    position: number,
    outcome: ProgressOutcome,
    selfReportedLevel?: number | null,
  ) => Promise<ProgressFeedback | null>;
  progressFeedback: ProgressFeedback | null;
  progressFeedbackTarget: { position: number; targetSkill: string } | null;
  clearProgressFeedback: () => void;
  reset: () => void;
};

const Ctx = createContext<IntelligenceContext | null>(null);

type LaunchOpts = {
  role: string;
  roleName: string;
  weeklyHours: number;
  learningStyle: string;
  withDemoEvidence: boolean;
  experienceLevel?: string;
  interests?: string[];
  goalText?: string;
  intakeSkills?: Array<{ skill: string; observed_level: number }>;
};

function readStored(): SessionSnapshot | null {
  if (typeof window === "undefined") return null;
  try {
    const raw = sessionStorage.getItem(STORAGE_KEY);
    return raw ? (JSON.parse(raw) as SessionSnapshot) : null;
  } catch {
    return null;
  }
}

function writeStored(snapshot: SessionSnapshot | null) {
  if (typeof window === "undefined") return;
  if (!snapshot) {
    sessionStorage.removeItem(STORAGE_KEY);
    return;
  }
  sessionStorage.setItem(STORAGE_KEY, JSON.stringify(snapshot));
}

function snapshotGaps(items: GapItem[]): GapSnapshot[] {
  return items.map((item) => ({
    skill: item.skill,
    name: item.name,
    evidence_state: item.evidence_state,
    attainment: item.attainment,
    proficiency: item.proficiency,
    target_level: item.target_level,
    action: item.action,
    blocked: item.blocked,
  }));
}

export function IntelligenceProvider({ children }: { children: ReactNode }) {
  const [hydrated, setHydrated] = useState(false);
  const [learnerId, setLearnerId] = useState<string | null>(null);
  const [displayName, setDisplayName] = useState("");
  const [role, setRole] = useState("ai-ml-engineer");
  const [roleName, setRoleName] = useState("AI/ML Engineer");
  const [weeklyHours, setWeeklyHours] = useState(8);
  const [learningStyle, setLearningStyle] = useState("MIXED");
  const [view, setViewState] = useState<ViewId>("overview");
  const [v1PathId, setV1PathId] = useState<string | null>(null);
  const [gaps, setGaps] = useState<GapItem[]>([]);
  const [dashboard, setDashboard] = useState<Dashboard | null>(null);
  const [paths, setPaths] = useState<PathRead[]>([]);
  const [timeline, setTimeline] = useState<TimelineEntry[]>([]);
  const [suggested, setSuggested] = useState<SuggestedAssessment | null>(null);
  const [assessment, setAssessment] = useState<AssessmentPublic | null>(null);
  const [attempt, setAttempt] = useState<AssessmentAttempt | null>(null);
  const [diff, setDiff] = useState<PathDiff | null>(null);
  const [beforeGaps, setBeforeGaps] = useState<GapSnapshot[]>([]);
  const [skills, setSkills] = useState<FusedSkill[]>([]);
  const [judgeMode, setJudgeMode] = useState(false);
  const [loading, setLoading] = useState(false);
  const [mutating, setMutating] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [updatingModel, setUpdatingModel] = useState(false);
  const [progressFeedback, setProgressFeedback] = useState<ProgressFeedback | null>(null);
  const [progressFeedbackTarget, setProgressFeedbackTarget] = useState<{
    position: number;
    targetSkill: string;
  } | null>(null);

  const persist = useCallback(
    (next: Partial<SessionSnapshot> & { learnerId: string }) => {
      const snapshot: SessionSnapshot = {
        learnerId: next.learnerId,
        displayName: next.displayName ?? displayName,
        role: next.role ?? role,
        roleName: next.roleName ?? roleName,
        weeklyHours: next.weeklyHours ?? weeklyHours,
        learningStyle: next.learningStyle ?? learningStyle,
        v1PathId: next.v1PathId === undefined ? v1PathId : next.v1PathId,
        view: next.view ?? view,
      };
      writeStored(snapshot);
    },
    [displayName, role, roleName, weeklyHours, learningStyle, v1PathId, view],
  );

  const setView = useCallback(
    (next: ViewId) => {
      setViewState(next);
      if (learnerId) {
        persist({ learnerId, view: next });
      }
    },
    [learnerId, persist],
  );

  const refresh = useCallback(async () => {
    if (!learnerId) return;
    setLoading(true);
    setError(null);
    try {
      const [gapProfile, pathList, time, suggest, skillRows, dash] = await Promise.all([
        api.gaps(learnerId, role),
        api.paths(learnerId),
        api.timeline(learnerId, role),
        api.suggested(learnerId, role),
        api.skills(learnerId),
        api.dashboard(learnerId, role),
      ]);
      setGaps(gapProfile.items);
      setRoleName(gapProfile.name);
      setPaths(pathList);
      setTimeline(time);
      setSuggested(suggest);
      setSkills(skillRows);
      setDashboard(dash);
      const active = pathList.find((item) => item.status === "ACTIVE") ?? null;
      if (active && pathList.some((item) => item.version > 1)) {
        const diffBody = await api.pathDiff(learnerId, active.id);
        setDiff(diffBody);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load intelligence");
    } finally {
      setLoading(false);
    }
  }, [learnerId, role]);

  useEffect(() => {
    const stored = readStored();
    if (stored) {
      setLearnerId(stored.learnerId);
      setDisplayName(stored.displayName);
      setRole(stored.role);
      setRoleName(stored.roleName);
      setWeeklyHours(stored.weeklyHours);
      setLearningStyle(stored.learningStyle);
      setV1PathId(stored.v1PathId);
      setViewState(stored.view);
    }
    if (typeof window !== "undefined") {
      setJudgeMode(sessionStorage.getItem(JUDGE_KEY) === "1");
    }
    setHydrated(true);
  }, []);

  useEffect(() => {
    if (!hydrated || !learnerId) return;
    void refresh();
  }, [hydrated, learnerId, refresh]);

  const bootstrapLearner = useCallback(
    async (opts: LaunchOpts & { demo: boolean }) => {
      setMutating(true);
      setError(null);
      try {
        const tag = opts.demo ? "pathfinder-live-demo" : "pathfinder-learner";
        const learner = await api.createLearner({
          display_name: `${tag}-${crypto.randomUUID().slice(0, 6)}`,
          experience_level: opts.experienceLevel,
          weekly_hours: opts.weeklyHours,
          learning_style: opts.learningStyle,
          interests: opts.interests,
          goal_text: opts.goalText,
          target_role: opts.role,
        });
        if (opts.withDemoEvidence) {
          let demoRows;
          try {
            demoRows = await api.demoEvidence(opts.role);
          } catch (err) {
            if (err instanceof ApiError && err.status === 404) {
              throw new Error(
                `Demo evidence API not found (/v1/roles/${opts.role}/demo-evidence). Restart the backend with the latest code.`,
              );
            }
            throw err;
          }
          for (const row of demoRows) {
            await api.addEvidence(learner.id, {
              skill: row.skill,
              source: row.source,
              observed_level: row.observed_level,
              confidence: row.confidence,
            });
          }
        }
        if (opts.intakeSkills?.length) {
          for (const row of opts.intakeSkills) {
            await api.addEvidence(learner.id, {
              skill: row.skill,
              source: "SELF_REPORT",
              observed_level: row.observed_level,
              confidence: 0.7,
            });
          }
        }
        const path = await api.createPath(learner.id, {
          role: opts.role,
          weekly_hours: opts.weeklyHours,
          learning_style: opts.learningStyle,
        });
        const first = path.items.find((item) => item.executable && item.kind === "EXECUTABLE");
        if (first) {
          await api.completeItem(learner.id, path.id, first.position);
        }
        setLearnerId(learner.id);
        setDisplayName(learner.display_name);
        setRole(opts.role);
        setRoleName(opts.roleName);
        setWeeklyHours(opts.weeklyHours);
        setLearningStyle(opts.learningStyle);
        setV1PathId(path.id);
        setViewState("overview");
        persist({
          learnerId: learner.id,
          displayName: learner.display_name,
          role: opts.role,
          roleName: opts.roleName,
          weeklyHours: opts.weeklyHours,
          learningStyle: opts.learningStyle,
          v1PathId: path.id,
          view: "overview",
        });
        const [gapProfile, pathList, time, suggest, skillRows, dash] = await Promise.all([
          api.gaps(learner.id, opts.role),
          api.paths(learner.id),
          api.timeline(learner.id, opts.role),
          api.suggested(learner.id, opts.role),
          api.skills(learner.id),
          api.dashboard(learner.id, opts.role),
        ]);
        setGaps(gapProfile.items);
        setRoleName(gapProfile.name);
        setPaths(pathList);
        setTimeline(time);
        setSuggested(suggest);
        setSkills(skillRows);
        setDashboard(dash);
      } catch (err) {
        setError(err instanceof Error ? err.message : "Could not start PathFinder");
        throw err;
      } finally {
        setMutating(false);
      }
    },
    [persist],
  );

  const launchDemo = useCallback(
    async (opts?: Partial<LaunchOpts> & { role?: string; weeklyHours?: number; learningStyle?: string }) => {
      const roleSlug = opts?.role ?? "ai-ml-engineer";
      await bootstrapLearner({
        role: roleSlug,
        roleName: opts?.roleName ?? roleSlug,
        weeklyHours: opts?.weeklyHours ?? 8,
        learningStyle: opts?.learningStyle ?? "MIXED",
        withDemoEvidence: opts?.withDemoEvidence ?? true,
        experienceLevel: opts?.experienceLevel,
        interests: opts?.interests,
        goalText: opts?.goalText,
        intakeSkills: opts?.intakeSkills,
        demo: true,
      });
    },
    [bootstrapLearner],
  );

  const startCustom = useCallback(
    async (opts: LaunchOpts) => {
      await bootstrapLearner({ ...opts, demo: false });
    },
    [bootstrapLearner],
  );

  const completeFirstExecutable = useCallback(async () => {
    if (!learnerId) return;
    const active = paths.find((item) => item.status === "ACTIVE");
    const first = active?.items.find((item) => item.executable && item.status !== "COMPLETED");
    if (!active || !first) return;
    await api.completeItem(learnerId, active.id, first.position);
    await refresh();
  }, [learnerId, paths, refresh]);

  const loadAssessment = useCallback(async (slug: string) => {
    setMutating(true);
    setError(null);
    try {
      setBeforeGaps(snapshotGaps(gaps));
      const spec = await api.assessment(slug);
      setAssessment(spec);
      setView("assess");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not load assessment");
    } finally {
      setMutating(false);
    }
  }, [gaps, setView]);

  const submitAnswers = useCallback(
    async (answers: number[]) => {
      if (!learnerId || !assessment) return;
      setUpdatingModel(true);
      setError(null);
      try {
        const result = await api.submitAttempt(learnerId, assessment.slug, answers);
        setAttempt(result);
        if (result.diff) setDiff(result.diff);
        else if (result.path_id) {
          const body = await api.pathDiff(learnerId, result.path_id);
          setDiff(body);
        }
        await refresh();
        setView("result");
      } catch (err) {
        setError(err instanceof Error ? err.message : "Assessment submit failed");
      } finally {
        setUpdatingModel(false);
      }
    },
    [learnerId, assessment, refresh, setView],
  );

  const launchJudgeDemo = useCallback(
    async (opts?: Partial<LaunchOpts> & { role?: string; weeklyHours?: number; learningStyle?: string }) => {
      if (typeof window !== "undefined") {
        sessionStorage.setItem(JUDGE_KEY, "1");
      }
      setJudgeMode(true);
      const roleSlug = opts?.role ?? "ai-ml-engineer";
      await bootstrapLearner({
        role: roleSlug,
        roleName: opts?.roleName ?? roleSlug,
        weeklyHours: opts?.weeklyHours ?? 8,
        learningStyle: opts?.learningStyle ?? "MIXED",
        withDemoEvidence: opts?.withDemoEvidence ?? true,
        experienceLevel: opts?.experienceLevel,
        interests: opts?.interests,
        goalText: opts?.goalText,
        intakeSkills: opts?.intakeSkills,
        demo: true,
      });
    },
    [bootstrapLearner],
  );

  const loadEvidence = useCallback(async (skill: string) => {
    if (!learnerId) return [];
    return api.evidence(learnerId, skill);
  }, [learnerId]);

  const recordProgress = useCallback(
    async (
      pathId: string,
      position: number,
      outcome: ProgressOutcome,
      selfReportedLevel?: number | null,
    ) => {
      if (!learnerId) return null;
      setUpdatingModel(true);
      setError(null);
      try {
        setBeforeGaps(snapshotGaps(gaps));
        const payload: {
          path_id: string;
          position: number;
          outcome: ProgressOutcome;
          self_reported_level?: number;
        } = { path_id: pathId, position, outcome };
        if (selfReportedLevel != null) {
          payload.self_reported_level = selfReportedLevel;
        }
        const body = await api.progress(learnerId, payload);
        if (body.adaptation === "CREATED" && body.new_path_id) {
          const diffBody = await api.pathDiff(learnerId, body.new_path_id);
          setDiff(diffBody);
        }
        setProgressFeedbackTarget({ position, targetSkill: body.target_skill });
        setProgressFeedback(body);
        await refresh();
        return body;
      } catch (err) {
        setError(err instanceof Error ? err.message : "Progress feedback failed");
        throw err;
      } finally {
        setUpdatingModel(false);
      }
    },
    [learnerId, gaps, refresh],
  );

  const clearProgressFeedback = useCallback(() => {
    setProgressFeedback(null);
    setProgressFeedbackTarget(null);
  }, []);

  const reset = useCallback(() => {
    writeStored(null);
    if (typeof window !== "undefined") {
      sessionStorage.removeItem(JUDGE_KEY);
    }
    setJudgeMode(false);
    setLearnerId(null);
    setDisplayName("");
    setGaps([]);
    setDashboard(null);
    setPaths([]);
    setTimeline([]);
    setSuggested(null);
    setAssessment(null);
    setAttempt(null);
    setDiff(null);
    setBeforeGaps([]);
    setSkills([]);
    setV1PathId(null);
    setViewState("overview");
    setProgressFeedback(null);
    setProgressFeedbackTarget(null);
  }, []);

  const activePath = useMemo(
    () => paths.find((item) => item.status === "ACTIVE") ?? null,
    [paths],
  );
  const previousPath = useMemo(() => {
    if (v1PathId) {
      return paths.find((item) => item.id === v1PathId) ?? null;
    }
    const superseded = paths.filter((item) => item.status === "SUPERSEDED");
    return superseded.sort((a, b) => a.version - b.version)[0] ?? null;
  }, [paths, v1PathId]);

  const value: IntelligenceContext = {
    learnerId,
    hydrated,
    displayName,
    role,
    roleName,
    weeklyHours,
    learningStyle,
    view,
    gaps,
    dashboard,
    paths,
    activePath,
    previousPath,
    timeline,
    suggested,
    assessment,
    attempt,
    diff,
    beforeGaps,
    skills,
    judgeMode,
    loading,
    mutating,
    error,
    updatingModel,
    setView,
    refresh,
    launchDemo,
    launchJudgeDemo,
    startCustom,
    completeFirstExecutable,
    loadAssessment,
    submitAnswers,
    loadEvidence,
    recordProgress,
    progressFeedback,
    progressFeedbackTarget,
    clearProgressFeedback,
    reset,
  };

  return <Ctx.Provider value={value}>{children}</Ctx.Provider>;
}

export function useIntelligence() {
  const ctx = useContext(Ctx);
  if (!ctx) throw new Error("useIntelligence must be used within IntelligenceProvider");
  return ctx;
}

import { fireEvent, render, screen, waitFor, type RenderResult } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import {
  canShowProgressActions,
  isFrozenPathItem,
  ProgressActions,
} from "@/components/path/ProgressActions";
import type { PathItem } from "@/lib/types";

const progress = vi.fn();
const pathDiff = vi.fn();
const setView = vi.fn();
const recordProgress = vi.fn();
const clearProgressFeedback = vi.fn();
let updatingModel = false;
let progressFeedback: import("@/lib/types").ProgressFeedback | null = null;
let progressFeedbackTarget: { position: number; targetSkill: string } | null = null;

function mockProgressResult(body: import("@/lib/types").ProgressFeedback) {
  recordProgress.mockImplementation(async () => {
    progressFeedback = body;
    progressFeedbackTarget = { position: body.position, targetSkill: body.target_skill };
    return body;
  });
}

async function expectProgressResult(
  rerender: RenderResult["rerender"],
  testId: "progress-result-stable" | "progress-result-created",
  item: PathItem = executable,
  pathId = "path-1",
) {
  await waitFor(() => expect(recordProgress).toHaveBeenCalled());
  rerender(<ProgressActions item={item} pathId={pathId} />);
  await waitFor(() => expect(screen.getByTestId(testId)).toBeInTheDocument());
}

const executable: PathItem = {
  position: 2,
  week: 1,
  status: "PENDING",
  resource: "khan-statistics-probability",
  title: "Statistics & Probability",
  type: "RESOURCE",
  target_skill: "statistics",
  intervention: "FOUNDATION",
  eligibility: "ELIGIBLE",
  duration_hours: 18,
  url: null,
  score_breakdown: {},
  explanation: "Close the statistics gap.",
  prerequisites: [],
  causality: {},
  kind: "EXECUTABLE",
  executable: true,
  gate: null,
};

const waiting: PathItem = {
  ...executable,
  position: 4,
  status: "WAITING_FOR_VERIFICATION",
  title: "Serve sklearn model lab",
  target_skill: "model_deployment",
  eligibility: "BLOCKED_BY_UNKNOWN",
  executable: false,
  kind: "WAITING_FOR_VERIFICATION",
  prerequisites: [{ skill: "docker", min_level: 0.6, state: "UNKNOWN", observed: null }],
};

const completed: PathItem = {
  ...executable,
  position: 0,
  status: "COMPLETED",
};

vi.mock("@/lib/api", () => ({
  api: {
    progress: (...args: unknown[]) => progress(...args),
    pathDiff: (...args: unknown[]) => pathDiff(...args),
  },
}));

vi.mock("@/lib/session", () => ({
  useIntelligence: () => ({
    recordProgress,
    updatingModel,
    setView,
    progressFeedback,
    progressFeedbackTarget,
    clearProgressFeedback,
  }),
}));

describe("progress action helpers", () => {
  it("shows actions only on executable items", () => {
    expect(canShowProgressActions(executable)).toBe(true);
    expect(canShowProgressActions(waiting)).toBe(false);
    expect(canShowProgressActions(completed)).toBe(false);
    expect(isFrozenPathItem(completed)).toBe(true);
  });
});

describe("ProgressActions", () => {
  beforeEach(() => {
    updatingModel = false;
    progressFeedback = null;
    progressFeedbackTarget = null;
    progress.mockReset();
    pathDiff.mockReset();
    recordProgress.mockReset();
    clearProgressFeedback.mockReset();
    setView.mockReset();
  });

  it("renders complete struggled skip on executable items", () => {
    render(<ProgressActions item={executable} pathId="path-1" />);
    expect(screen.getByTestId("progress-actions")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Complete" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "I struggled" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Skip" })).toBeInTheDocument();
  });

  it("does not render actions on waiting items", () => {
    render(<ProgressActions item={waiting} pathId="path-1" />);
    expect(screen.queryByTestId("progress-actions")).not.toBeInTheDocument();
  });

  it("shows frozen work on completed items", () => {
    render(<ProgressActions item={completed} pathId="path-1" />);
    expect(screen.getByTestId("progress-frozen")).toHaveTextContent("Frozen work");
  });

  it("shows confidence for complete", () => {
    render(<ProgressActions item={executable} pathId="path-1" />);
    fireEvent.click(screen.getByRole("button", { name: "Complete" }));
    expect(screen.getByTestId("progress-confidence")).toBeInTheDocument();
    expect(screen.getByLabelText("How confident are you now?")).toBeInTheDocument();
  });

  it("shows confidence for struggled", () => {
    render(<ProgressActions item={executable} pathId="path-1" />);
    fireEvent.click(screen.getByRole("button", { name: "I struggled" }));
    expect(screen.getByTestId("progress-confidence")).toBeInTheDocument();
  });

  it("submits skip without confidence surface", async () => {
    mockProgressResult({
      path_id: "path-1",
      position: 2,
      outcome: "SKIPPED",
      item_status: "SKIPPED",
      target_skill: "statistics",
      evidence_recorded: false,
      observed_level: null,
      adaptation: "NO_ADAPTATION_REQUIRED",
      new_path_id: null,
      diff: null,
      summary: "Recorded.",
    });
    render(<ProgressActions item={executable} pathId="path-1" />);
    fireEvent.click(screen.getByRole("button", { name: "Skip" }));
    await waitFor(() => expect(recordProgress).toHaveBeenCalledWith("path-1", 2, "SKIPPED", null));
    expect(screen.queryByTestId("progress-confidence")).not.toBeInTheDocument();
  });

  it("submits exact backend payload on complete", async () => {
    mockProgressResult({
      path_id: "path-1",
      position: 2,
      outcome: "COMPLETED",
      item_status: "COMPLETED",
      target_skill: "statistics",
      evidence_recorded: true,
      observed_level: 0.65,
      adaptation: "NO_ADAPTATION_REQUIRED",
      new_path_id: null,
      diff: null,
      summary: "Recorded.",
    });
    render(<ProgressActions item={executable} pathId="path-1" />);
    fireEvent.click(screen.getByRole("button", { name: "Complete" }));
    fireEvent.click(screen.getByRole("button", { name: "Submit progress" }));
    await waitFor(() =>
      expect(recordProgress).toHaveBeenCalledWith("path-1", 2, "COMPLETED", 0.65),
    );
  });

  it("disables controls while updating", () => {
    updatingModel = true;
    render(<ProgressActions item={executable} pathId="path-1" />);
    expect(screen.getByRole("button", { name: "Complete" })).toBeDisabled();
    expect(screen.getByRole("button", { name: "Skip" })).toBeDisabled();
  });

  it("renders stable path state when adaptation is not required", async () => {
    mockProgressResult({
      path_id: "path-1",
      position: 2,
      outcome: "SKIPPED",
      item_status: "SKIPPED",
      target_skill: "statistics",
      evidence_recorded: false,
      observed_level: null,
      adaptation: "NO_ADAPTATION_REQUIRED",
      new_path_id: null,
      diff: null,
      summary: "Recorded.",
    });
    const { rerender } = render(<ProgressActions item={executable} pathId="path-1" />);
    fireEvent.click(screen.getByRole("button", { name: "Skip" }));
    await expectProgressResult(rerender, "progress-result-stable");
    rerender(<ProgressActions item={{ ...executable, status: "COMPLETED" }} pathId="path-1" />);
    expect(screen.getByTestId("progress-result-stable")).toBeInTheDocument();
    expect(screen.queryByTestId("progress-frozen")).not.toBeInTheDocument();
    expect(screen.getByText(/did not need to change/i)).toBeInTheDocument();
  });

  it("renders path-change state when adaptation is created", async () => {
    mockProgressResult({
      path_id: "path-1",
      position: 2,
      outcome: "STRUGGLED",
      item_status: "IN_PROGRESS",
      target_skill: "statistics",
      evidence_recorded: true,
      observed_level: 0.2,
      adaptation: "CREATED",
      new_path_id: "path-2",
      diff: { added: [], removed: [], moved: [], unchanged: [], blocked: [], changed_skills: [] },
      summary: "Path re-planned.",
    });
    const { rerender } = render(<ProgressActions item={executable} pathId="path-1" />);
    fireEvent.click(screen.getByRole("button", { name: "I struggled" }));
    fireEvent.click(screen.getByRole("button", { name: "Submit progress" }));
    await expectProgressResult(rerender, "progress-result-created");
    rerender(<ProgressActions item={{ ...executable, status: "COMPLETED" }} pathId="path-2" />);
    expect(screen.getByTestId("progress-result-created")).toBeInTheDocument();
    expect(screen.queryByTestId("progress-frozen")).not.toBeInTheDocument();
    expect(screen.getByText("Path changed")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "See what changed" }));
    expect(setView).toHaveBeenCalledWith("changed");
  });

  it("renders actionable error when backend fails", async () => {
    recordProgress.mockRejectedValue(new Error("Feedback applies to the active path only"));
    render(<ProgressActions item={executable} pathId="path-1" />);
    fireEvent.click(screen.getByRole("button", { name: "Skip" }));
    await waitFor(() => expect(screen.getByTestId("progress-error")).toBeInTheDocument());
    expect(screen.getByRole("alert")).toHaveTextContent("active path");
  });

  it("does not call api.progress directly from the component", async () => {
    mockProgressResult({
      path_id: "path-1",
      position: 2,
      outcome: "SKIPPED",
      item_status: "SKIPPED",
      target_skill: "statistics",
      evidence_recorded: false,
      observed_level: null,
      adaptation: "NO_ADAPTATION_REQUIRED",
      new_path_id: null,
      diff: null,
      summary: "Recorded.",
    });
    render(<ProgressActions item={executable} pathId="path-1" />);
    fireEvent.click(screen.getByRole("button", { name: "Skip" }));
    await waitFor(() => expect(recordProgress).toHaveBeenCalled());
    expect(progress).not.toHaveBeenCalled();
  });

  it("does not compute path diff client-side", async () => {
    mockProgressResult({
      adaptation: "NO_ADAPTATION_REQUIRED",
      summary: "ok",
      path_id: "path-1",
      position: 2,
      outcome: "SKIPPED",
      item_status: "SKIPPED",
      target_skill: "statistics",
      evidence_recorded: false,
      observed_level: null,
      new_path_id: null,
      diff: null,
    });
    render(<ProgressActions item={executable} pathId="path-1" />);
    fireEvent.click(screen.getByRole("button", { name: "Skip" }));
    await waitFor(() => expect(recordProgress).toHaveBeenCalled());
    expect(pathDiff).not.toHaveBeenCalled();
  });

  it("keeps surfaces within document width", () => {
    const { container } = render(<ProgressActions item={executable} pathId="path-1" />);
    const surface = container.querySelector(".progress-surface");
    expect(surface).toBeTruthy();
    expect(surface?.className).toContain("max-w-full");
  });

  it("keeps result visible after item leaves executable state", async () => {
    mockProgressResult({
      path_id: "path-1",
      position: 2,
      outcome: "STRUGGLED",
      item_status: "IN_PROGRESS",
      target_skill: "statistics",
      evidence_recorded: true,
      observed_level: 0.15,
      adaptation: "CREATED",
      new_path_id: "path-2",
      diff: { added: [], removed: [], moved: [], unchanged: [], blocked: [], changed_skills: [] },
      summary: "Path re-planned.",
    });
    const blocked: PathItem = {
      ...executable,
      status: "IN_PROGRESS",
      executable: false,
      kind: "WAITING_FOR_REMEDIATION",
      eligibility: "BLOCKED_BY_GAP",
    };
    const { rerender } = render(<ProgressActions item={executable} pathId="path-1" />);
    fireEvent.click(screen.getByRole("button", { name: "I struggled" }));
    fireEvent.click(screen.getByRole("button", { name: "Submit progress" }));
    await expectProgressResult(rerender, "progress-result-created");
    rerender(<ProgressActions item={blocked} pathId="path-2" />);
    expect(screen.getByTestId("progress-result-created")).toBeInTheDocument();
    expect(screen.queryByTestId("progress-actions")).not.toBeInTheDocument();
  });

  it("uses static adaptation chain without motion classes", async () => {
    mockProgressResult({
      path_id: "path-1",
      position: 2,
      outcome: "STRUGGLED",
      item_status: "IN_PROGRESS",
      target_skill: "statistics",
      evidence_recorded: true,
      observed_level: 0.2,
      adaptation: "CREATED",
      new_path_id: "path-2",
      diff: null,
      summary: "Path re-planned.",
    });
    const { rerender } = render(<ProgressActions item={executable} pathId="path-1" />);
    fireEvent.click(screen.getByRole("button", { name: "I struggled" }));
    fireEvent.click(screen.getByRole("button", { name: "Submit progress" }));
    await expectProgressResult(rerender, "progress-result-created");
    const chain = screen.getByLabelText("Adaptation sequence");
    expect(chain.className).not.toMatch(/animate|transition/);
  });
});

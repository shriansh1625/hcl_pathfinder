import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { GoalIntelligenceField } from "@/components/onboarding/GoalIntelligenceField";
import type { GoalIntake } from "@/lib/types";

const baseIntake: GoalIntake = {
  goal_text: "test goal",
  role: null,
  role_alternatives: [],
  skills: [],
  ungraded: [],
  weekly_hours: null,
  timeframe_weeks: null,
  learning_style: null,
  unresolved: [],
  source: "DETERMINISTIC",
  provider: "rules",
  model: "keyword-resolver",
  resolution_status: "UNSUPPORTED",
};

describe("GoalIntelligenceField", () => {
  it("shows resolved state with canonical role", async () => {
    const resolved: GoalIntake = {
      ...baseIntake,
      resolution_status: "RESOLVED",
      role: { slug: "cybersecurity-analyst", name: "Cybersecurity Analyst", mention: "cybersecurity", how: "ALIAS" },
    };
    const onResolve = vi.fn().mockResolvedValue(resolved);

    render(
      <GoalIntelligenceField
        goalText="I want to be a penetration tester"
        onGoalTextChange={() => undefined}
        busy={false}
        onResolve={onResolve}
        onManual={() => undefined}
        resolvedIntake={resolved}
        onContinueFromResolution={() => undefined}
        onSelectAmbiguousRole={() => undefined}
        onSeeSupportedCareers={() => undefined}
      />,
    );

    fireEvent.click(screen.getByRole("button", { name: /Resolve goal/i }));
    expect(await screen.findByText("Goal understood")).toBeTruthy();
    expect(screen.getByText("Cybersecurity Analyst")).toBeTruthy();
  });

  it("shows ambiguous candidates without dead-ending", async () => {
    const ambiguous: GoalIntake = {
      ...baseIntake,
      resolution_status: "AMBIGUOUS",
      role_alternatives: [
        { slug: "data-engineer", name: "Data Engineer", mention: "data", how: "ALIAS" },
        { slug: "data-analyst", name: "Data Analyst", mention: "data", how: "ALIAS" },
      ],
    };
    const onSelect = vi.fn();
    const onResolve = vi.fn().mockResolvedValue(ambiguous);

    render(
      <GoalIntelligenceField
        goalText="I want a career in data"
        onGoalTextChange={() => undefined}
        busy={false}
        onResolve={onResolve}
        onManual={() => undefined}
        resolvedIntake={ambiguous}
        onContinueFromResolution={() => undefined}
        onSelectAmbiguousRole={onSelect}
        onSeeSupportedCareers={() => undefined}
      />,
    );

    fireEvent.click(screen.getByRole("button", { name: /Resolve goal/i }));
    expect(await screen.findByText(/Which route fits your goal/i)).toBeTruthy();
    fireEvent.click(screen.getByRole("button", { name: /Data Engineer/i }));
    expect(onSelect).toHaveBeenCalledWith("data-engineer");
  });

  it("shows unsupported recovery actions", async () => {
    const unsupported: GoalIntake = {
      ...baseIntake,
      resolution_status: "UNSUPPORTED",
      unresolved: ["quantum potato"],
    };
    const onManual = vi.fn();
    const onResolve = vi.fn().mockResolvedValue(unsupported);

    render(
      <GoalIntelligenceField
        goalText="quantum potato infrastructure architect"
        onGoalTextChange={() => undefined}
        busy={false}
        onResolve={onResolve}
        onManual={onManual}
        resolvedIntake={unsupported}
        onContinueFromResolution={() => undefined}
        onSelectAmbiguousRole={() => undefined}
        onSeeSupportedCareers={() => undefined}
      />,
    );

    fireEvent.click(screen.getByRole("button", { name: /Resolve goal/i }));
    expect(await screen.findByText(/Goal not mapped yet/i)).toBeTruthy();
    fireEvent.click(screen.getByRole("button", { name: /Pick career manually/i }));
    expect(onManual).toHaveBeenCalled();
  });

  it("shows validation when resolve is clicked with empty goal", () => {
    render(
      <GoalIntelligenceField
        goalText=""
        onGoalTextChange={() => undefined}
        busy={false}
        onResolve={vi.fn()}
        onManual={() => undefined}
        resolvedIntake={null}
        onContinueFromResolution={() => undefined}
        onSelectAmbiguousRole={() => undefined}
        onSeeSupportedCareers={() => undefined}
      />,
    );

    fireEvent.click(screen.getByRole("button", { name: /Resolve goal/i }));
    expect(screen.getByRole("alert")).toHaveTextContent(/at least a few words/i);
  });

  it("calls onManual even while parent busy state is true", () => {
    const onManual = vi.fn();

    render(
      <GoalIntelligenceField
        goalText=""
        onGoalTextChange={() => undefined}
        busy={true}
        onResolve={vi.fn()}
        onManual={onManual}
        resolvedIntake={null}
        onContinueFromResolution={() => undefined}
        onSelectAmbiguousRole={() => undefined}
        onSeeSupportedCareers={() => undefined}
      />,
    );

    fireEvent.click(screen.getByRole("button", { name: /Pick career manually/i }));
    expect(onManual).toHaveBeenCalled();
  });

  it("calls onResolve when resolve is clicked with valid goal", async () => {
    const onResolve = vi.fn().mockResolvedValue({
      ...baseIntake,
      resolution_status: "RESOLVED",
      role: { slug: "ai-ml-engineer", name: "AI/ML Engineer", mention: "ml", how: "ALIAS" },
    });

    render(
      <GoalIntelligenceField
        goalText="I want to become an ML engineer focused on computer vision"
        onGoalTextChange={() => undefined}
        busy={false}
        onResolve={onResolve}
        onManual={() => undefined}
        resolvedIntake={null}
        onContinueFromResolution={() => undefined}
        onSelectAmbiguousRole={() => undefined}
        onSeeSupportedCareers={() => undefined}
      />,
    );

    expect(screen.getByRole("button", { name: /Resolve goal/i })).toBeEnabled();
    fireEvent.click(screen.getByRole("button", { name: /Resolve goal/i }));
    expect(onResolve).toHaveBeenCalledTimes(1);
    expect(await screen.findByText("Goal understood")).toBeTruthy();
    expect(screen.getByText("AI/ML Engineer")).toBeTruthy();
  });

  it("shows error recovery and preserves goal text after API failure", async () => {
    const onResolve = vi.fn().mockRejectedValue(new Error("network down"));
    const onManual = vi.fn();

    render(
      <GoalIntelligenceField
        goalText="I want to become a penetration tester"
        onGoalTextChange={() => undefined}
        busy={false}
        onResolve={onResolve}
        onManual={onManual}
        resolvedIntake={null}
        onContinueFromResolution={() => undefined}
        onSelectAmbiguousRole={() => undefined}
        onSeeSupportedCareers={() => undefined}
      />,
    );

    fireEvent.click(screen.getByRole("button", { name: /Resolve goal/i }));
    expect(await screen.findByRole("alert")).toHaveTextContent(/did not complete/i);
    expect(screen.getByRole("textbox")).toHaveValue("I want to become a penetration tester");
    fireEvent.click(screen.getByRole("button", { name: /Pick career manually/i }));
    expect(onManual).toHaveBeenCalled();
  });

  it("re-enables resolve after failure for retry", async () => {
    const onResolve = vi
      .fn()
      .mockRejectedValueOnce(new Error("temporary"))
      .mockResolvedValueOnce({
        ...baseIntake,
        resolution_status: "RESOLVED",
        role: { slug: "cybersecurity-analyst", name: "Cybersecurity Analyst", mention: "cyber", how: "ALIAS" },
      });

    render(
      <GoalIntelligenceField
        goalText="cybersecurity analyst cloud security"
        onGoalTextChange={() => undefined}
        busy={false}
        onResolve={onResolve}
        onManual={() => undefined}
        resolvedIntake={null}
        onContinueFromResolution={() => undefined}
        onSelectAmbiguousRole={() => undefined}
        onSeeSupportedCareers={() => undefined}
      />,
    );

    fireEvent.click(screen.getByRole("button", { name: /Resolve goal/i }));
    await screen.findByRole("alert");
    const retry = screen.getByRole("button", { name: /Resolve goal/i });
    expect(retry).toBeEnabled();
    fireEvent.click(retry);
    expect(await screen.findByText("Goal understood")).toBeTruthy();
    expect(onResolve).toHaveBeenCalledTimes(2);
  });
});

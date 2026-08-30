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
});

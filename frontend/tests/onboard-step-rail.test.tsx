import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { OnboardStepRail } from "@/components/onboarding/OnboardStepRail";

describe("OnboardStepRail", () => {
  it("renders bounded step labels without floating pill backgrounds", () => {
    const { container } = render(<OnboardStepRail step={5} />);
    expect(screen.getByText("Evidence")).toHaveClass("onboard-step-label");
    expect(container.querySelector(".bg-paper")).toBeNull();
    expect(container.querySelector(".onboard-step-rail")).toBeTruthy();
    expect(container.querySelector(".onboard-step-item.is-active")).toBeTruthy();
  });
});

import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { StageStepperBar } from "./StageStepperBar";
import type { StageStepData } from "./stageStepperBarInterface";

vi.mock("@/core/hooks/useReducedMotion", () => ({
  useReducedMotion: () => false,
}));

const SAMPLE_STAGES: readonly StageStepData[] = [
  { stageName: "Router", status: "completed", durationSeconds: 10 },
  { stageName: "Research", status: "completed", durationSeconds: 45 },
  { stageName: "Transcript", status: "active", durationSeconds: 30 },
  { stageName: "Content", status: "pending" },
  { stageName: "Layout", status: "pending" },
  { stageName: "FFmpeg", status: "pending" },
  { stageName: "Assembly", status: "pending" },
];

describe("StageStepperBar", () => {
  it("should render all stages", () => {
    // Arrange & Act
    render(
      <StageStepperBar stages={SAMPLE_STAGES} activeStageIndex={2} onStageClick={vi.fn()} />,
    );

    // Assert
    const listItems = screen.getByTestId("stage-stepper-bar").querySelectorAll("li");
    expect(listItems).toHaveLength(7);
  });

  it("should render as an ordered list", () => {
    // Arrange & Act
    render(
      <StageStepperBar stages={SAMPLE_STAGES} activeStageIndex={0} onStageClick={vi.fn()} />,
    );

    // Assert
    const orderedList = screen.getByTestId("stage-stepper-bar");
    expect(orderedList.tagName).toBe("OL");
  });

  it("should set aria-current on the active stage", () => {
    // Arrange & Act
    render(
      <StageStepperBar stages={SAMPLE_STAGES} activeStageIndex={2} onStageClick={vi.fn()} />,
    );

    // Assert
    const listItems = screen.getByTestId("stage-stepper-bar").querySelectorAll("li");
    expect(listItems[2]).toHaveAttribute("aria-current", "step");
    expect(listItems[0]).not.toHaveAttribute("aria-current");
  });

  it("should call onStageClick with correct index", async () => {
    // Arrange
    const handleStageClick = vi.fn();
    const user = userEvent.setup();
    render(
      <StageStepperBar stages={SAMPLE_STAGES} activeStageIndex={0} onStageClick={handleStageClick} />,
    );

    // Act
    const stageButtons = screen.getAllByTestId("stage-step");
    await user.click(stageButtons[1]!);

    // Assert
    expect(handleStageClick).toHaveBeenCalledWith(1);
  });

  it("should display stage names", () => {
    // Arrange & Act
    render(
      <StageStepperBar stages={SAMPLE_STAGES} activeStageIndex={0} onStageClick={vi.fn()} />,
    );

    // Assert
    expect(screen.getByText("Router")).toBeInTheDocument();
    expect(screen.getByText("Assembly")).toBeInTheDocument();
  });

  it("should have a navigation landmark", () => {
    // Arrange & Act
    render(
      <StageStepperBar stages={SAMPLE_STAGES} activeStageIndex={0} onStageClick={vi.fn()} />,
    );

    // Assert
    expect(screen.getByRole("navigation")).toHaveAttribute("aria-label", "Pipeline stages");
  });
});

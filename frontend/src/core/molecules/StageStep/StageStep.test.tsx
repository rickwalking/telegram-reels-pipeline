import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { StageStep } from "./StageStep";
import type { StageStepStatus } from "./stageStepInterface";

vi.mock("@/core/hooks/useReducedMotion", () => ({
  useReducedMotion: () => false,
}));

describe("StageStep", () => {
  const STATUS_VARIANTS: readonly StageStepStatus[] = [
    "pending",
    "active",
    "completed",
    "failed",
    "paused",
  ];

  it.each(STATUS_VARIANTS)("should render %s status variant", (status) => {
    // Arrange & Act
    render(<StageStep stageName="router" status={status} onClick={vi.fn()} />);

    // Assert
    const stepElement = screen.getByTestId("stage-step");
    expect(stepElement).toHaveAttribute("data-status", status);
  });

  it("should display the stage name", () => {
    // Arrange & Act
    render(<StageStep stageName="research" status="active" onClick={vi.fn()} />);

    // Assert
    expect(screen.getByText("research")).toBeInTheDocument();
  });

  it("should display formatted duration when provided", () => {
    // Arrange & Act
    render(
      <StageStep stageName="router" status="completed" durationSeconds={125} onClick={vi.fn()} />,
    );

    // Assert
    expect(screen.getByTestId("stage-duration")).toHaveTextContent("2m 5s");
  });

  it("should apply tabular-nums to duration", () => {
    // Arrange & Act
    render(
      <StageStep stageName="router" status="completed" durationSeconds={30} onClick={vi.fn()} />,
    );

    // Assert
    const durationElement = screen.getByTestId("stage-duration");
    expect(durationElement.style.fontVariantNumeric).toBe("tabular-nums");
  });

  it("should not display duration when not provided", () => {
    // Arrange & Act
    render(<StageStep stageName="router" status="pending" onClick={vi.fn()} />);

    // Assert
    expect(screen.queryByTestId("stage-duration")).not.toBeInTheDocument();
  });

  it("should call onClick when clicked", async () => {
    // Arrange
    const handleClick = vi.fn();
    const user = userEvent.setup();
    render(<StageStep stageName="router" status="active" onClick={handleClick} />);

    // Act
    await user.click(screen.getByTestId("stage-step"));

    // Assert
    expect(handleClick).toHaveBeenCalledOnce();
  });

  it("should set aria-expanded when active", () => {
    // Arrange & Act
    render(<StageStep stageName="router" status="active" isActive onClick={vi.fn()} />);

    // Assert
    expect(screen.getByTestId("stage-step")).toHaveAttribute("aria-expanded", "true");
  });

  it("should have a pulse animation on active status circle", () => {
    // Arrange & Act
    render(<StageStep stageName="router" status="active" isActive onClick={vi.fn()} />);

    // Assert
    const circle = screen.getByTestId("status-circle");
    expect(circle.className).toContain("animate-pulse");
  });

  it("should have minimum 44px touch target", () => {
    // Arrange & Act
    render(<StageStep stageName="router" status="pending" onClick={vi.fn()} />);

    // Assert
    const buttonElement = screen.getByTestId("stage-step");
    expect(buttonElement.className).toContain("min-h-[44px]");
    expect(buttonElement.className).toContain("min-w-[44px]");
  });
});

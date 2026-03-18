import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { TimelineEventMarker } from "./TimelineEventMarker";
import type { PipelineEventItem } from "@/services/interfaces/pipelineEventApiInterface";

const SAMPLE_EVENT: PipelineEventItem = {
  eventId: "evt-abc123",
  pipelineRunId: "run-001",
  timestamp: "2026-03-18T10:00:00Z",
  eventName: "pipeline.stage_entered",
  stage: "router",
  payload: { attempt: 1 },
};

describe("TimelineEventMarker", () => {
  it("renders a button with aria-label containing event name", () => {
    // Arrange & Act
    render(
      <TimelineEventMarker
        event={SAMPLE_EVENT}
        isSelected={false}
        onSelect={vi.fn()}
      />,
    );
    const buttonElement = screen.getByRole("button");

    // Assert
    expect(buttonElement).toHaveAttribute(
      "aria-label",
      expect.stringContaining("pipeline.stage_entered"),
    );
  });

  it("has minimum touch target size via CSS classes", () => {
    // Arrange & Act
    render(
      <TimelineEventMarker
        event={SAMPLE_EVENT}
        isSelected={false}
        onSelect={vi.fn()}
      />,
    );
    const buttonElement = screen.getByRole("button");

    // Assert
    expect(buttonElement.className).toContain("min-w-11");
    expect(buttonElement.className).toContain("min-h-11");
  });

  it("calls onSelect with eventId when clicked", async () => {
    // Arrange
    const handleSelect = vi.fn();
    const userSetup = userEvent.setup();
    render(
      <TimelineEventMarker
        event={SAMPLE_EVENT}
        isSelected={false}
        onSelect={handleSelect}
      />,
    );

    // Act
    await userSetup.click(screen.getByRole("button"));

    // Assert
    expect(handleSelect).toHaveBeenCalledWith("evt-abc123");
  });

  it("shows aria-pressed true when selected", () => {
    // Arrange & Act
    render(
      <TimelineEventMarker
        event={SAMPLE_EVENT}
        isSelected={true}
        onSelect={vi.fn()}
      />,
    );

    // Assert
    expect(screen.getByRole("button")).toHaveAttribute(
      "aria-pressed",
      "true",
    );
  });

  it("displays short event name label", () => {
    // Arrange & Act
    render(
      <TimelineEventMarker
        event={SAMPLE_EVENT}
        isSelected={false}
        onSelect={vi.fn()}
      />,
    );

    // Assert
    expect(screen.getByText("stage_entered")).toBeInTheDocument();
  });

  it("renders color dot indicator", () => {
    // Arrange & Act
    const { container } = render(
      <TimelineEventMarker
        event={SAMPLE_EVENT}
        isSelected={false}
        onSelect={vi.fn()}
      />,
    );
    const dotElement = container.querySelector("[aria-hidden='true']");

    // Assert
    expect(dotElement).toBeInTheDocument();
    expect(dotElement?.className).toContain("rounded-full");
  });
});

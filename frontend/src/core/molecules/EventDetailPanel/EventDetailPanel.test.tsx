import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { EventDetailPanel } from "./EventDetailPanel";
import type { PipelineEventItem } from "@/services/interfaces/pipelineEventApiInterface";

const SAMPLE_EVENT: PipelineEventItem = {
  eventId: "evt-abc123",
  pipelineRunId: "run-001",
  timestamp: "2026-03-18T10:00:00Z",
  eventName: "pipeline.stage_entered",
  stage: "router",
  payload: { attempt: 1 },
};

describe("EventDetailPanel", () => {
  it("shows empty state when no event is selected", () => {
    // Arrange & Act
    render(<EventDetailPanel selectedEvent={null} onClose={vi.fn()} />);

    // Assert
    expect(
      screen.getByText("Select an event to view details"),
    ).toBeInTheDocument();
  });

  it("displays event name when event is provided", () => {
    // Arrange & Act
    render(<EventDetailPanel selectedEvent={SAMPLE_EVENT} onClose={vi.fn()} />);

    // Assert
    expect(screen.getByText("pipeline.stage_entered")).toBeInTheDocument();
  });

  it("displays event ID with copy button", () => {
    // Arrange & Act
    render(<EventDetailPanel selectedEvent={SAMPLE_EVENT} onClose={vi.fn()} />);

    // Assert
    expect(screen.getByText("evt-abc123")).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: "Copy ID" }),
    ).toBeInTheDocument();
  });

  it("displays timestamp in a time element", () => {
    // Arrange & Act
    render(<EventDetailPanel selectedEvent={SAMPLE_EVENT} onClose={vi.fn()} />);
    const timeElement = screen.getByText("2026-03-18T10:00:00Z");

    // Assert
    expect(timeElement.tagName).toBe("TIME");
  });

  it("displays stage when present", () => {
    // Arrange & Act
    render(<EventDetailPanel selectedEvent={SAMPLE_EVENT} onClose={vi.fn()} />);

    // Assert
    expect(screen.getByText("router")).toBeInTheDocument();
  });

  it("hides stage when null", () => {
    // Arrange
    const eventWithoutStage = { ...SAMPLE_EVENT, stage: null };

    // Act
    render(
      <EventDetailPanel selectedEvent={eventWithoutStage} onClose={vi.fn()} />,
    );

    // Assert
    expect(screen.queryByText("Stage")).not.toBeInTheDocument();
  });

  it("displays JSON payload viewer", () => {
    // Arrange & Act
    render(<EventDetailPanel selectedEvent={SAMPLE_EVENT} onClose={vi.fn()} />);

    // Assert
    expect(screen.getByText("Payload")).toBeInTheDocument();
  });

  it("calls onClose when close button is clicked", async () => {
    // Arrange
    const handleClose = vi.fn();
    const userSetup = userEvent.setup();
    render(
      <EventDetailPanel selectedEvent={SAMPLE_EVENT} onClose={handleClose} />,
    );

    // Act
    await userSetup.click(
      screen.getByRole("button", { name: "Close detail panel" }),
    );

    // Assert
    expect(handleClose).toHaveBeenCalledOnce();
  });

  it("has accessible panel role via aside", () => {
    // Arrange & Act
    render(<EventDetailPanel selectedEvent={SAMPLE_EVENT} onClose={vi.fn()} />);

    // Assert
    expect(
      screen.getByRole("complementary", { name: "Event detail panel" }),
    ).toBeInTheDocument();
  });
});

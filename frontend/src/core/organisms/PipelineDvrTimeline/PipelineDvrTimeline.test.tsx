import { render, screen, fireEvent } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { PipelineDvrTimeline } from "./PipelineDvrTimeline";
import type { PipelineEventItem } from "@/services/interfaces/pipelineEventApiInterface";
import type { StageBoundaryData } from "@/core/atoms/StageBoundaryMarker/stageBoundaryMarkerInterface";

function createTestEvent(
  index: number,
  stage: string | null = "router",
): PipelineEventItem {
  return {
    eventId: `evt-${index}`,
    pipelineRunId: "run-001",
    timestamp: `2026-03-18T10:0${index}:00Z`,
    eventName: `pipeline.event_${index}`,
    stage,
    payload: { index },
  };
}

const THREE_EVENTS: PipelineEventItem[] = [
  createTestEvent(0),
  createTestEvent(1),
  createTestEvent(2),
];

const ROUTER_BOUNDARY: StageBoundaryData[] = [
  {
    stageName: "ROUTER",
    startedAt: "2026-03-18T10:00:00Z",
    durationSeconds: 30,
    eventIndex: 0,
  },
];

describe("PipelineDvrTimeline", () => {
  it("renders loading state", () => {
    // Arrange & Act
    render(
      <PipelineDvrTimeline
        events={[]}
        boundaries={[]}
        selectedEventId={null}
        onSelectEvent={vi.fn()}
        isLoading={true}
        errorMessage={null}
        onRetry={vi.fn()}
      />,
    );

    // Assert
    expect(screen.getByRole("status")).toHaveTextContent("Loading events...");
  });

  it("renders error state with retry button", async () => {
    // Arrange
    const handleRetry = vi.fn();
    const userSetup = userEvent.setup();
    render(
      <PipelineDvrTimeline
        events={[]}
        boundaries={[]}
        selectedEventId={null}
        onSelectEvent={vi.fn()}
        isLoading={false}
        errorMessage="Network failure"
        onRetry={handleRetry}
      />,
    );

    // Act
    await userSetup.click(screen.getByText("Retry"));

    // Assert
    expect(screen.getByRole("alert")).toHaveTextContent("Network failure");
    expect(handleRetry).toHaveBeenCalledOnce();
  });

  it("renders empty state when no events", () => {
    // Arrange & Act
    render(
      <PipelineDvrTimeline
        events={[]}
        boundaries={[]}
        selectedEventId={null}
        onSelectEvent={vi.fn()}
        isLoading={false}
        errorMessage={null}
        onRetry={vi.fn()}
      />,
    );

    // Assert
    expect(
      screen.getByText("No events recorded for this run."),
    ).toBeInTheDocument();
  });

  it("renders event markers for each event", () => {
    // Arrange & Act
    render(
      <PipelineDvrTimeline
        events={THREE_EVENTS}
        boundaries={[]}
        selectedEventId={null}
        onSelectEvent={vi.fn()}
        isLoading={false}
        errorMessage={null}
        onRetry={vi.fn()}
      />,
    );

    // Assert
    const allButtons = screen.getAllByRole("button");
    expect(allButtons).toHaveLength(3);
  });

  it("calls onSelectEvent when a marker is clicked", async () => {
    // Arrange
    const handleSelect = vi.fn();
    const userSetup = userEvent.setup();
    render(
      <PipelineDvrTimeline
        events={THREE_EVENTS}
        boundaries={[]}
        selectedEventId={null}
        onSelectEvent={handleSelect}
        isLoading={false}
        errorMessage={null}
        onRetry={vi.fn()}
      />,
    );

    // Act
    const firstButton = screen.getAllByRole("button")[0];
    if (firstButton === undefined) throw new Error("No buttons found");
    await userSetup.click(firstButton);

    // Assert
    expect(handleSelect).toHaveBeenCalledWith("evt-0");
  });

  it("navigates to next event with ArrowRight key", () => {
    // Arrange
    const handleSelect = vi.fn();
    render(
      <PipelineDvrTimeline
        events={THREE_EVENTS}
        boundaries={[]}
        selectedEventId="evt-0"
        onSelectEvent={handleSelect}
        isLoading={false}
        errorMessage={null}
        onRetry={vi.fn()}
      />,
    );

    // Act
    const toolbarElement = screen.getByRole("toolbar");
    fireEvent.keyDown(toolbarElement, { key: "ArrowRight" });

    // Assert
    expect(handleSelect).toHaveBeenCalledWith("evt-1");
  });

  it("wraps to last event with ArrowLeft from first", () => {
    // Arrange
    const handleSelect = vi.fn();
    render(
      <PipelineDvrTimeline
        events={THREE_EVENTS}
        boundaries={[]}
        selectedEventId="evt-0"
        onSelectEvent={handleSelect}
        isLoading={false}
        errorMessage={null}
        onRetry={vi.fn()}
      />,
    );

    // Act
    const toolbarElement = screen.getByRole("toolbar");
    fireEvent.keyDown(toolbarElement, { key: "ArrowLeft" });

    // Assert
    expect(handleSelect).toHaveBeenCalledWith("evt-2");
  });

  it("shows virtualization notice for >50 events", () => {
    // Arrange
    const manyEvents = Array.from({ length: 60 }, (_, index) =>
      createTestEvent(index),
    );

    // Act
    render(
      <PipelineDvrTimeline
        events={manyEvents}
        boundaries={[]}
        selectedEventId={null}
        onSelectEvent={vi.fn()}
        isLoading={false}
        errorMessage={null}
        onRetry={vi.fn()}
      />,
    );

    // Assert
    expect(
      screen.getByText(/Showing 50 of 60 events/),
    ).toBeInTheDocument();
  });

  it("renders stage boundary markers", () => {
    // Arrange & Act
    render(
      <PipelineDvrTimeline
        events={THREE_EVENTS}
        boundaries={ROUTER_BOUNDARY}
        selectedEventId={null}
        onSelectEvent={vi.fn()}
        isLoading={false}
        errorMessage={null}
        onRetry={vi.fn()}
      />,
    );

    // Assert
    expect(screen.getByText("ROUTER")).toBeInTheDocument();
  });

  it("has accessible toolbar role", () => {
    // Arrange & Act
    render(
      <PipelineDvrTimeline
        events={THREE_EVENTS}
        boundaries={[]}
        selectedEventId={null}
        onSelectEvent={vi.fn()}
        isLoading={false}
        errorMessage={null}
        onRetry={vi.fn()}
      />,
    );

    // Assert
    expect(
      screen.getByRole("toolbar", { name: "Pipeline event timeline" }),
    ).toBeInTheDocument();
  });
});

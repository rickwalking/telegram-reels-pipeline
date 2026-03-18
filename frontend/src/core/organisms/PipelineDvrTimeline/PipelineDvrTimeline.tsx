import { useCallback, useRef } from "react";
import { TimelineEventMarker } from "@/core/atoms/TimelineEventMarker/TimelineEventMarker";
import { StageBoundaryMarker } from "@/core/atoms/StageBoundaryMarker/StageBoundaryMarker";
import type { StageBoundaryData } from "@/core/atoms/StageBoundaryMarker/stageBoundaryMarkerInterface";
import type { PipelineDvrTimelineProps } from "./pipelineDvrTimelineInterface";

const VIRTUALIZATION_THRESHOLD = 50;

export function PipelineDvrTimeline({
  events,
  boundaries,
  selectedEventId,
  onSelectEvent,
  isLoading,
  errorMessage,
  onRetry,
}: PipelineDvrTimelineProps) {
  const timelineContainerRef = useRef<HTMLDivElement>(null);

  const handleMarkerSelect = useCallback(
    (eventId: string) => {
      const nextValue = eventId === selectedEventId ? null : eventId;
      onSelectEvent(nextValue);
    },
    [onSelectEvent, selectedEventId],
  );

  const handleKeyboardNavigation = useCallback(
    (keyboardEvent: React.KeyboardEvent) => {
      if (events.length === 0) return;

      const currentIndex = events.findIndex(
        (eventItem) => eventItem.eventId === selectedEventId,
      );

      if (keyboardEvent.key === "ArrowRight" || keyboardEvent.key === "ArrowDown") {
        keyboardEvent.preventDefault();
        const nextIndex = currentIndex < events.length - 1 ? currentIndex + 1 : 0;
        const nextEvent = events[nextIndex];
        if (nextEvent === undefined) return;
        onSelectEvent(nextEvent.eventId);
        focusMarkerAtIndex(timelineContainerRef, nextIndex);
      }

      if (keyboardEvent.key === "ArrowLeft" || keyboardEvent.key === "ArrowUp") {
        keyboardEvent.preventDefault();
        const previousIndex = currentIndex > 0 ? currentIndex - 1 : events.length - 1;
        const previousEvent = events[previousIndex];
        if (previousEvent === undefined) return;
        onSelectEvent(previousEvent.eventId);
        focusMarkerAtIndex(timelineContainerRef, previousIndex);
      }
    },
    [events, selectedEventId, onSelectEvent],
  );

  if (isLoading) {
    return (
      <div className="flex items-center justify-center p-8 text-muted-foreground text-sm" role="status">
        Loading events...
      </div>
    );
  }

  if (errorMessage !== null) {
    return (
      <div className="flex flex-col items-center justify-center gap-3 p-8 text-sm" role="alert">
        <p className="text-destructive">Failed to load events: {errorMessage}</p>
        <button
          type="button"
          className="px-4 py-1.5 rounded-md border border-border bg-background hover:bg-muted cursor-pointer text-sm"
          onClick={onRetry}
        >
          Retry
        </button>
      </div>
    );
  }

  if (events.length === 0) {
    return (
      <div className="flex items-center justify-center p-8 text-muted-foreground text-sm">
        No events recorded for this run.
      </div>
    );
  }

  const shouldVirtualize = events.length > VIRTUALIZATION_THRESHOLD;
  const boundaryMap = buildBoundaryMap(boundaries);
  const renderedEvents = shouldVirtualize
    ? events.slice(0, VIRTUALIZATION_THRESHOLD)
    : events;

  return (
    <div
      ref={timelineContainerRef}
      className="flex flex-col gap-1 p-3 overflow-y-auto max-h-full"
      role="toolbar"
      aria-label="Pipeline event timeline"
      aria-orientation="horizontal"
      tabIndex={0}
      onKeyDown={handleKeyboardNavigation}
    >
      {renderedEvents.map((eventItem, eventIndex) => (
        <div key={eventItem.eventId}>
          {boundaryMap.has(eventIndex) ? (
            <StageBoundaryMarker boundary={boundaryMap.get(eventIndex)!} />
          ) : null}
          <TimelineEventMarker
            event={eventItem}
            isSelected={eventItem.eventId === selectedEventId}
            onSelect={handleMarkerSelect}
          />
        </div>
      ))}
      {shouldVirtualize ? (
        <div className="py-2 text-center text-xs text-muted-foreground italic">
          Showing {VIRTUALIZATION_THRESHOLD} of {events.length} events
        </div>
      ) : null}
    </div>
  );
}

function buildBoundaryMap(
  boundaries: readonly StageBoundaryData[],
): Map<number, StageBoundaryData> {
  const boundaryMap = new Map<number, StageBoundaryData>();
  for (const boundary of boundaries) {
    boundaryMap.set(boundary.eventIndex, boundary);
  }
  return boundaryMap;
}

function focusMarkerAtIndex(
  containerRef: React.RefObject<HTMLDivElement | null>,
  targetIndex: number,
): void {
  const containerElement = containerRef.current;
  if (containerElement === null) return;
  const allMarkerButtons = containerElement.querySelectorAll(
    'button[aria-label^="Event:"]',
  );
  const targetButton = allMarkerButtons[targetIndex] as
    | HTMLElement
    | undefined;
  targetButton?.focus();
}

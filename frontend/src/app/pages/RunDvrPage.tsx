import { useCallback, useMemo, useState } from "react";
import { useParams } from "@tanstack/react-router";
import { runDvrRoute } from "@/app/routes/routeTree";
import { useServices } from "@/app/hooks/useServices";
import { PipelineDvrTimeline } from "@/core/organisms/PipelineDvrTimeline/PipelineDvrTimeline";
import { EventDetailPanel } from "@/core/molecules/EventDetailPanel/EventDetailPanel";
import type { PipelineEventItem } from "@/services/interfaces/pipelineEventApiInterface";
import type { StageBoundaryData } from "@/core/atoms/StageBoundaryMarker/stageBoundaryMarkerInterface";
import { deriveStageBoundaries } from "@/utils/deriveStageBoundaries";

interface EventListState {
  readonly events: readonly PipelineEventItem[];
  readonly boundaries: readonly StageBoundaryData[];
  readonly total: number;
  readonly isLoading: boolean;
  readonly errorMessage: string | null;
}

const INITIAL_STATE: EventListState = {
  events: [],
  boundaries: [],
  total: 0,
  isLoading: false,
  errorMessage: null,
};

export function RunDvrPage() {
  const { runId } = useParams({ from: runDvrRoute.id });
  const { pipelineEventApi } = useServices();
  const [listState, setListState] = useState<EventListState>(INITIAL_STATE);
  const [selectedEventId, setSelectedEventId] = useState<string | null>(null);

  const loadEvents = useCallback(() => {
    setListState((previous) => ({ ...previous, isLoading: true, errorMessage: null }));

    pipelineEventApi
      .fetchEventList(runId, 0, 200)
      .then((response) => {
        const derivedBoundaries = deriveStageBoundaries(response.items);
        setListState({
          events: response.items,
          boundaries: derivedBoundaries,
          total: response.total,
          isLoading: false,
          errorMessage: null,
        });
      })
      .catch((thrownError: unknown) => {
        const message =
          thrownError instanceof Error ? thrownError.message : "Unknown error";
        setListState((previous) => ({
          ...previous,
          isLoading: false,
          errorMessage: message,
        }));
      });
  }, [runId, pipelineEventApi]);

  const handleClosePanel = useCallback(() => {
    setSelectedEventId(null);
  }, []);

  const selectedEvent: PipelineEventItem | null = useMemo(() => {
    if (selectedEventId === null) return null;
    return (
      listState.events.find(
        (eventItem) => eventItem.eventId === selectedEventId,
      ) ?? null
    );
  }, [listState.events, selectedEventId]);

  return (
    <div className="flex flex-col h-[calc(100vh-3.5rem)]">
      <header className="flex items-center gap-3 px-4 py-3 border-b border-border shrink-0">
        <h1 className="text-lg font-bold m-0">Pipeline DVR</h1>
        <code className="text-xs text-muted-foreground">{runId}</code>
        <button
          type="button"
          className="px-3.5 py-1.5 rounded-md border border-border bg-background hover:bg-muted cursor-pointer text-sm"
          onClick={loadEvents}
        >
          {listState.events.length > 0 ? "Refresh" : "Load Events"}
        </button>
        {listState.total > 0 ? (
          <span className="text-xs text-muted-foreground ml-auto">
            {listState.total} events
          </span>
        ) : null}
      </header>
      <div className="flex flex-1 overflow-hidden max-md:flex-col">
        <div className="flex-1 overflow-y-auto min-w-[300px]">
          <PipelineDvrTimeline
            events={listState.events}
            boundaries={listState.boundaries}
            selectedEventId={selectedEventId}
            onSelectEvent={setSelectedEventId}
            isLoading={listState.isLoading}
            errorMessage={listState.errorMessage}
            onRetry={loadEvents}
          />
        </div>
        <div className="w-[400px] shrink-0 overflow-y-auto resize-x min-w-[280px] max-w-[600px] max-md:w-full max-md:min-w-0 max-md:max-w-full max-md:resize-none">
          <EventDetailPanel
            selectedEvent={selectedEvent}
            onClose={handleClosePanel}
          />
        </div>
      </div>
    </div>
  );
}

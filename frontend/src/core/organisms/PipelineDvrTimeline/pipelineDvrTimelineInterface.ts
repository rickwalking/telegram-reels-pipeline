import type { PipelineEventItem } from "@/services/interfaces/pipelineEventApiInterface";
import type { StageBoundaryData } from "@/core/atoms/StageBoundaryMarker/stageBoundaryMarkerInterface";

export interface PipelineDvrTimelineProps {
  readonly events: readonly PipelineEventItem[];
  readonly boundaries: readonly StageBoundaryData[];
  readonly selectedEventId: string | null;
  readonly onSelectEvent: (eventId: string | null) => void;
  readonly isLoading: boolean;
  readonly errorMessage: string | null;
  readonly onRetry: () => void;
}

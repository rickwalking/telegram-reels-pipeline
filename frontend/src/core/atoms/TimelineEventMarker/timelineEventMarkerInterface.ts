import type { PipelineEventItem } from "@/services/interfaces/pipelineEventApiInterface";

export interface TimelineEventMarkerProps {
  readonly event: PipelineEventItem;
  readonly isSelected: boolean;
  readonly onSelect: (eventId: string) => void;
}

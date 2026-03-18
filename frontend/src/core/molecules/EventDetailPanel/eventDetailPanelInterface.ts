import type { PipelineEventItem } from "@/services/interfaces/pipelineEventApiInterface";

export interface EventDetailPanelProps {
  readonly selectedEvent: PipelineEventItem | null;
  readonly onClose: () => void;
}

import type { StatusBadgeVariant } from "@/core/atoms/statusBadge/statusBadgeInterface";

export interface RunListItemProps {
  readonly pipelineRunId: string;
  readonly youtubeUrl: string;
  readonly executionStatus: StatusBadgeVariant;
  readonly createdAt: string;
  readonly onPrefetch: () => void;
}

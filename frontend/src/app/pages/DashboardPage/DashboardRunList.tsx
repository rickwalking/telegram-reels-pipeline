import { useCallback } from "react";
import { usePipelineRunList, usePrefetchPipelineRunDetail } from "@/app/hooks/usePipelineRunList";
import { RunListItem } from "@/core/molecules/RunListItem/RunListItem";
import type { StatusBadgeVariant } from "@/core/atoms/statusBadge/statusBadgeInterface";

const VALID_STATUSES: ReadonlySet<string> = new Set([
  "pending", "active", "completed", "failed", "paused",
]);

function mapExecutionStatus(rawStatus: string): StatusBadgeVariant {
  if (VALID_STATUSES.has(rawStatus)) return rawStatus as StatusBadgeVariant;
  return "pending";
}

export function DashboardRunList() {
  const { data: pipelineRunList } = usePipelineRunList();
  const prefetchRunDetail = usePrefetchPipelineRunDetail();

  const createPrefetchHandler = useCallback(
    (pipelineRunId: string) => () => {
      prefetchRunDetail(pipelineRunId);
    },
    [prefetchRunDetail],
  );

  if (pipelineRunList.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center py-16 text-center" data-testid="empty-state">
        <p className="text-lg font-medium text-muted-foreground">No pipeline runs yet</p>
        <p className="text-sm text-muted-foreground mt-1">
          Trigger a new run to get started.
        </p>
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-2" data-testid="run-list">
      {pipelineRunList.map((runSummary) => (
        <RunListItem
          key={runSummary.pipelineRunId}
          pipelineRunId={runSummary.pipelineRunId}
          youtubeUrl={runSummary.youtubeUrl}
          executionStatus={mapExecutionStatus(runSummary.executionStatus)}
          createdAt={runSummary.createdAt}
          onPrefetch={createPrefetchHandler(runSummary.pipelineRunId)}
        />
      ))}
    </div>
  );
}

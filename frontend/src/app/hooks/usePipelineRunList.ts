import { useSuspenseQuery, useQueryClient } from "@tanstack/react-query";
import { useCallback } from "react";
import { useServices } from "@/app/hooks/useServices";
import type { PipelineRunSummary } from "@/services/interfaces/pipelineApiClientInterface";

const PIPELINE_RUN_LIST_QUERY_KEY = ["pipeline-run-list"] as const;

export function usePipelineRunList() {
  const { pipelineApiClient } = useServices();

  const queryResult = useSuspenseQuery<readonly PipelineRunSummary[]>({
    queryKey: PIPELINE_RUN_LIST_QUERY_KEY,
    queryFn: () => pipelineApiClient.fetchRunList({}),
  });

  return queryResult;
}

export function usePrefetchPipelineRunDetail() {
  const queryClient = useQueryClient();
  const { pipelineApiClient } = useServices();

  const prefetchRunDetail = useCallback(
    (pipelineRunId: string) => {
      queryClient.prefetchQuery({
        queryKey: ["pipeline-run-detail", pipelineRunId],
        queryFn: () => pipelineApiClient.fetchRunDetail(pipelineRunId),
      });
    },
    [queryClient, pipelineApiClient],
  );

  return prefetchRunDetail;
}

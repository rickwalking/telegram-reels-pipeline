import { useSuspenseQuery } from "@tanstack/react-query";
import { useServices } from "@/app/hooks/useServices";
import type { PipelineRunDetail } from "@/services/interfaces/pipelineApiClientInterface";

export function usePipelineRunDetail(pipelineRunId: string) {
  const { pipelineApiClient } = useServices();

  const queryResult = useSuspenseQuery<PipelineRunDetail>({
    queryKey: ["pipeline-run-detail", pipelineRunId],
    queryFn: () => pipelineApiClient.fetchRunDetail(pipelineRunId),
  });

  return queryResult;
}

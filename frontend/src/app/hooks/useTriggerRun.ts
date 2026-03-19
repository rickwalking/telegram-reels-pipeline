import { useState, useCallback } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { useServices } from "@/app/hooks/useServices";
import type { TriggerRunCommand } from "@/services/interfaces/pipelineApiClientInterface";

interface TriggerRunResult {
  readonly triggerPipelineRun: (command: TriggerRunCommand) => Promise<void>;
  readonly isSubmitting: boolean;
  readonly errorMessage: string | null;
}

export function useTriggerRun(): TriggerRunResult {
  const { pipelineApiClient } = useServices();
  const queryClient = useQueryClient();
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const triggerPipelineRun = useCallback(
    async (command: TriggerRunCommand) => {
      setIsSubmitting(true);
      setErrorMessage(null);
      try {
        await pipelineApiClient.triggerRun(command);
        await queryClient.invalidateQueries({ queryKey: ["pipeline-run-list"] });
      } catch (thrownError: unknown) {
        const message = thrownError instanceof Error
          ? thrownError.message
          : "Failed to trigger pipeline run";
        setErrorMessage(message);
      } finally {
        setIsSubmitting(false);
      }
    },
    [pipelineApiClient, queryClient],
  );

  return { triggerPipelineRun, isSubmitting, errorMessage };
}

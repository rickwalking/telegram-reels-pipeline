import { z } from "zod/v4";

export const pipelineRunSummarySchema = z
  .object({
    pipelineRunId: z.string().min(1),
    youtubeUrl: z.string().url(),
    executionStatus: z.string().min(1),
    currentStage: z.string().min(1),
    createdAt: z.string().min(1),
  });

export const pipelineRunDetailSchema = pipelineRunSummarySchema
  .extend({
    triggerSource: z.string(),
    currentAttemptCount: z.number().int().nonnegative(),
    completedStages: z.array(z.string()),
    escalationStatus: z.string(),
    lastUpdatedAt: z.string(),
    qaEvaluationStatus: z.string(),
  });

export const pipelineRunSummaryListSchema = z.array(pipelineRunSummarySchema);

export type PipelineRunSummaryPayload = z.infer<typeof pipelineRunSummarySchema>;
export type PipelineRunDetailPayload = z.infer<typeof pipelineRunDetailSchema>;

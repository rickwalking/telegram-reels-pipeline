import { z } from "zod/v4";

export const pipelineRunSummarySchema = z
  .object({
    pipelineRunId: z.string().min(1),
    youtubeUrl: z.url(),
    executionStatus: z.string().min(1),
    currentStage: z.string().min(1),
    createdAt: z.iso.datetime(),
  })
  .strict();

export const pipelineRunDetailSchema = pipelineRunSummarySchema
  .extend({
    triggerSource: z.string().min(1),
    currentAttemptCount: z.number().int().nonnegative(),
    completedStages: z.array(z.string().min(1)),
    escalationStatus: z.string().min(1),
    lastUpdatedAt: z.iso.datetime(),
  })
  .strict();

export const pipelineRunSummaryListSchema = z.array(pipelineRunSummarySchema);

export type PipelineRunSummaryPayload = z.infer<
  typeof pipelineRunSummarySchema
>;
export type PipelineRunDetailPayload = z.infer<typeof pipelineRunDetailSchema>;

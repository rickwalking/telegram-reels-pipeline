import { z } from "zod/v4";

export const pipelineEventItemSchema = z
  .object({
    event_id: z.string().min(1),
    pipeline_run_id: z.string().min(1),
    timestamp: z.string().min(1),
    event_name: z.string().min(1),
    stage: z.string().nullable(),
    data: z.record(z.string(), z.unknown()),
  })
  .strict();

export const pipelineEventListResponseSchema = z
  .object({
    items: z.array(pipelineEventItemSchema),
    total: z.number().int().nonnegative(),
    offset: z.number().int().nonnegative(),
    limit: z.number().int().positive(),
  })
  .strict();

export type PipelineEventItemPayload = z.infer<
  typeof pipelineEventItemSchema
>;

export type PipelineEventListPayload = z.infer<
  typeof pipelineEventListResponseSchema
>;

import type {
  PipelineEventApiInterface,
  PipelineEventItem,
  PipelineEventListResponse,
} from "@/services/interfaces/pipelineEventApiInterface";
import {
  pipelineEventItemSchema,
  pipelineEventListResponseSchema,
} from "@/schemas/pipelineEventSchema";

const API_BASE_URL = "/api";

function mapPayloadToEventItem(
  raw: Record<string, unknown>,
): PipelineEventItem {
  return {
    eventId: raw.event_id as string,
    pipelineRunId: raw.pipeline_run_id as string,
    timestamp: raw.timestamp as string,
    eventName: raw.event_name as string,
    stage: raw.stage as string | null,
    payload: raw.data as Record<string, unknown>,
  };
}

async function parseJsonResponse(response: Response): Promise<unknown> {
  if (!response.ok) {
    const body = await response.text().catch(() => "Unknown error");
    throw new Error(`API error ${response.status}: ${body}`);
  }
  return response.json() as Promise<unknown>;
}

export class PipelineEventApiService implements PipelineEventApiInterface {
  async fetchEventList(
    pipelineRunId: string,
    offset: number,
    limit: number,
  ): Promise<PipelineEventListResponse> {
    const searchParams = new URLSearchParams({
      offset: String(offset),
      limit: String(limit),
    });
    const requestUrl = `${API_BASE_URL}/runs/${pipelineRunId}/events?${searchParams}`;
    const response = await fetch(requestUrl);
    const rawPayload = await parseJsonResponse(response);
    const validated = pipelineEventListResponseSchema.parse(rawPayload);

    return {
      items: validated.items.map(mapPayloadToEventItem),
      total: validated.total,
      offset: validated.offset,
      limit: validated.limit,
    };
  }

  async fetchEventDetail(
    pipelineRunId: string,
    eventId: string,
  ): Promise<PipelineEventItem> {
    const requestUrl = `${API_BASE_URL}/runs/${pipelineRunId}/events/${eventId}`;
    const response = await fetch(requestUrl);
    const rawPayload = await parseJsonResponse(response);
    const validated = pipelineEventItemSchema.parse(rawPayload);
    return mapPayloadToEventItem(validated as Record<string, unknown>);
  }
}

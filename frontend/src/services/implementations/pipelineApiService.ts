import type {
  PipelineApiClientInterface,
  PipelineRunDetail,
  PipelineRunSummary,
  RunListQueryParams,
  TriggerRunCommand,
} from "@/services/interfaces/pipelineApiClientInterface";
import {
  pipelineRunDetailSchema,
  pipelineRunSummaryListSchema,
} from "@/schemas/pipelineRunSchema";

const API_BASE_URL = "/api";

class PipelineApiError extends Error {
  readonly statusCode: number;

  constructor(message: string, statusCode: number) {
    super(message);
    this.name = "PipelineApiError";
    this.statusCode = statusCode;
  }
}

async function parseJsonResponse(response: Response): Promise<unknown> {
  if (!response.ok) {
    const body = await response.text().catch(() => "Unknown error");
    throw new PipelineApiError(body, response.status);
  }
  return response.json() as Promise<unknown>;
}

function buildRunListUrl(params: RunListQueryParams): string {
  const url = new URL(`${API_BASE_URL}/runs`, window.location.origin);
  if (params.executionStatus !== undefined) {
    url.searchParams.set("execution_status", params.executionStatus);
  }
  return url.toString();
}

export class PipelineApiService implements PipelineApiClientInterface {
  async fetchRunList(
    params: RunListQueryParams,
  ): Promise<readonly PipelineRunSummary[]> {
    const response = await fetch(buildRunListUrl(params));
    const data = await parseJsonResponse(response);
    return pipelineRunSummaryListSchema.parse(data);
  }

  async fetchRunDetail(pipelineRunId: string): Promise<PipelineRunDetail> {
    const response = await fetch(`${API_BASE_URL}/runs/${pipelineRunId}`);
    const data = await parseJsonResponse(response);
    return pipelineRunDetailSchema.parse(data);
  }

  async triggerRun(command: TriggerRunCommand): Promise<PipelineRunDetail> {
    const response = await fetch(`${API_BASE_URL}/runs`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        youtube_url: command.youtubeUrl,
        topic_focus: command.topicFocus,
      }),
    });
    const data = await parseJsonResponse(response);
    return pipelineRunDetailSchema.parse(data);
  }

  async pauseRun(pipelineRunId: string): Promise<void> {
    const response = await fetch(
      `${API_BASE_URL}/runs/${pipelineRunId}/pause`,
      { method: "POST" },
    );
    if (!response.ok) {
      const body = await response.text().catch(() => "Unknown error");
      throw new PipelineApiError(body, response.status);
    }
  }

  async resumeRun(pipelineRunId: string): Promise<void> {
    const response = await fetch(
      `${API_BASE_URL}/runs/${pipelineRunId}/resume`,
      { method: "POST" },
    );
    if (!response.ok) {
      const body = await response.text().catch(() => "Unknown error");
      throw new PipelineApiError(body, response.status);
    }
  }
}

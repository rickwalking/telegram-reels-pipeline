export interface PipelineEventItem {
  readonly eventId: string;
  readonly pipelineRunId: string;
  readonly timestamp: string;
  readonly eventName: string;
  readonly stage: string | null;
  readonly payload: Record<string, unknown>;
}

export interface PipelineEventListResponse {
  readonly items: readonly PipelineEventItem[];
  readonly total: number;
  readonly offset: number;
  readonly limit: number;
}

export interface PipelineEventApiInterface {
  fetchEventList(
    pipelineRunId: string,
    offset: number,
    limit: number,
  ): Promise<PipelineEventListResponse>;

  fetchEventDetail(
    pipelineRunId: string,
    eventId: string,
  ): Promise<PipelineEventItem>;
}

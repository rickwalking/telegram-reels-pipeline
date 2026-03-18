export interface SseEvent {
  readonly eventType: string;
  readonly payload: string;
  readonly timestamp: string;
}

export type SseEventHandler = (event: SseEvent) => void;
export type SseErrorHandler = (error: Error) => void;

export interface SseSubscription {
  readonly unsubscribe: () => void;
}

export interface SseClientInterface {
  subscribe(
    pipelineRunId: string,
    onEvent: SseEventHandler,
    onError: SseErrorHandler,
  ): SseSubscription;
}

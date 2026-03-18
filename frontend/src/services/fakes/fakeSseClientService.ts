import type {
  SseClientInterface,
  SseEvent,
  SseEventHandler,
  SseErrorHandler,
  SseSubscription,
} from "@/services/interfaces/sseClientInterface";

export class FakeSseClientService implements SseClientInterface {
  private eventHandler: SseEventHandler | null = null;
  private errorHandler: SseErrorHandler | null = null;
  public subscribeCallCount = 0;
  public unsubscribeCallCount = 0;

  subscribe(
    _pipelineRunId: string,
    onEvent: SseEventHandler,
    onError: SseErrorHandler,
  ): SseSubscription {
    this.subscribeCallCount += 1;
    this.eventHandler = onEvent;
    this.errorHandler = onError;

    return {
      unsubscribe: () => {
        this.unsubscribeCallCount += 1;
        this.eventHandler = null;
        this.errorHandler = null;
      },
    };
  }

  /** Simulate sending an event from the server. */
  emitEvent(event: SseEvent): void {
    this.eventHandler?.(event);
  }

  /** Simulate an SSE connection error. */
  emitError(error: Error): void {
    this.errorHandler?.(error);
  }
}

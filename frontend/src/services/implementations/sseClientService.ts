import type {
  SseClientInterface,
  SseEventHandler,
  SseErrorHandler,
  SseSubscription,
} from "@/services/interfaces/sseClientInterface";

const SSE_BASE_URL = "/api/runs";

function parseSseMessageData(rawData: string): {
  eventType: string;
  payload: string;
  timestamp: string;
} {
  try {
    const parsed = JSON.parse(rawData) as Record<string, unknown>;
    return {
      eventType: String(parsed["event_type"] ?? "unknown"),
      payload: String(parsed["payload"] ?? ""),
      timestamp: String(parsed["timestamp"] ?? new Date().toISOString()),
    };
  } catch {
    return {
      eventType: "unknown",
      payload: rawData,
      timestamp: new Date().toISOString(),
    };
  }
}

export class SseClientService implements SseClientInterface {
  subscribe(
    pipelineRunId: string,
    onEvent: SseEventHandler,
    onError: SseErrorHandler,
  ): SseSubscription {
    const eventSource = new EventSource(
      `${SSE_BASE_URL}/${pipelineRunId}/events`,
    );

    eventSource.onmessage = (messageEvent: MessageEvent<string>) => {
      const sseEvent = parseSseMessageData(messageEvent.data);
      onEvent(sseEvent);
    };

    eventSource.onerror = () => {
      onError(new Error(`SSE connection error for run ${pipelineRunId}`));
    };

    return {
      unsubscribe: () => eventSource.close(),
    };
  }
}

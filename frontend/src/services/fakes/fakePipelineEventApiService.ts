import type {
  PipelineEventApiInterface,
  PipelineEventItem,
  PipelineEventListResponse,
} from "@/services/interfaces/pipelineEventApiInterface";

function createFakeEventItem(
  overrides: Partial<PipelineEventItem> = {},
): PipelineEventItem {
  return {
    eventId: "evt-abc123",
    pipelineRunId: "run-001",
    timestamp: "2026-03-18T10:00:00Z",
    eventName: "pipeline.stage_entered",
    stage: "router",
    payload: { attempt: 1 },
    ...overrides,
  };
}

export class FakePipelineEventApiService
  implements PipelineEventApiInterface
{
  private readonly eventsByRun: Map<string, PipelineEventItem[]>;

  constructor() {
    this.eventsByRun = new Map([
      [
        "run-001",
        [
          createFakeEventItem({ eventId: "evt-001", eventName: "pipeline.stage_entered", stage: "router" }),
          createFakeEventItem({ eventId: "evt-002", eventName: "pipeline.stage_completed", stage: "router" }),
          createFakeEventItem({ eventId: "evt-003", eventName: "pipeline.stage_entered", stage: "research" }),
        ],
      ],
    ]);
  }

  async fetchEventList(
    pipelineRunId: string,
    offset: number,
    limit: number,
  ): Promise<PipelineEventListResponse> {
    const allEvents = this.eventsByRun.get(pipelineRunId) ?? [];
    const pageSlice = allEvents.slice(offset, offset + limit);

    return {
      items: pageSlice,
      total: allEvents.length,
      offset,
      limit,
    };
  }

  async fetchEventDetail(
    pipelineRunId: string,
    eventId: string,
  ): Promise<PipelineEventItem> {
    const allEvents = this.eventsByRun.get(pipelineRunId) ?? [];
    const matchedEvent = allEvents.find(
      (eventItem) => eventItem.eventId === eventId,
    );
    if (matchedEvent === undefined) {
      throw new Error(`Event ${eventId} not found`);
    }
    return matchedEvent;
  }
}

import type {
  PipelineApiClientInterface,
  PipelineRunDetail,
  PipelineRunSummary,
  RunListQueryParams,
  TriggerRunCommand,
} from "@/services/interfaces/pipelineApiClientInterface";

function createFakeRunSummary(
  overrides: Partial<PipelineRunSummary> = {},
): PipelineRunSummary {
  return {
    pipelineRunId: "run-001",
    youtubeUrl: "https://www.youtube.com/watch?v=test123",
    executionStatus: "active",
    currentStage: "research",
    createdAt: "2026-03-18T10:00:00Z",
    ...overrides,
  };
}

function createFakeRunDetail(
  overrides: Partial<PipelineRunDetail> = {},
): PipelineRunDetail {
  return {
    ...createFakeRunSummary(),
    triggerSource: "telegram",
    currentAttemptCount: 1,
    completedStages: ["router"],
    escalationStatus: "none",
    lastUpdatedAt: "2026-03-18T10:05:00Z",
    ...overrides,
  };
}

export class FakePipelineApiService implements PipelineApiClientInterface {
  private readonly runList: PipelineRunSummary[];
  private readonly runDetails: Map<string, PipelineRunDetail>;
  public triggerRunCallCount = 0;
  public pauseRunCallCount = 0;
  public resumeRunCallCount = 0;

  constructor() {
    this.runList = [
      createFakeRunSummary({ pipelineRunId: "run-001" }),
      createFakeRunSummary({
        pipelineRunId: "run-002",
        executionStatus: "completed",
      }),
    ];
    this.runDetails = new Map([
      ["run-001", createFakeRunDetail({ pipelineRunId: "run-001" })],
      [
        "run-002",
        createFakeRunDetail({
          pipelineRunId: "run-002",
          executionStatus: "completed",
        }),
      ],
    ]);
  }

  async fetchRunList(
    params: RunListQueryParams,
  ): Promise<readonly PipelineRunSummary[]> {
    if (params.executionStatus === undefined) {
      return this.runList;
    }
    return this.runList.filter(
      (run) => run.executionStatus === params.executionStatus,
    );
  }

  async fetchRunDetail(pipelineRunId: string): Promise<PipelineRunDetail> {
    const detail = this.runDetails.get(pipelineRunId);
    if (detail === undefined) {
      throw new Error(`Run ${pipelineRunId} not found`);
    }
    return detail;
  }

  async triggerRun(command: TriggerRunCommand): Promise<PipelineRunDetail> {
    this.triggerRunCallCount += 1;
    return createFakeRunDetail({
      pipelineRunId: "run-new",
      youtubeUrl: command.youtubeUrl,
      executionStatus: "pending",
      currentStage: "router",
    });
  }

  async pauseRun(_pipelineRunId: string): Promise<void> {
    this.pauseRunCallCount += 1;
  }

  async resumeRun(_pipelineRunId: string): Promise<void> {
    this.resumeRunCallCount += 1;
  }
}

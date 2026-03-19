export interface RunListQueryParams {
  readonly executionStatus?: string;
}

export interface PipelineRunSummary {
  readonly pipelineRunId: string;
  readonly youtubeUrl: string;
  readonly executionStatus: string;
  readonly currentStage: string;
  readonly createdAt: string;
}

export interface PipelineRunDetail extends PipelineRunSummary {
  readonly triggerSource: string;
  readonly currentAttemptCount: number;
  readonly completedStages: readonly string[];
  readonly escalationStatus: string;
  readonly lastUpdatedAt: string;
}

export interface TriggerRunCommand {
  readonly youtubeUrl: string;
  readonly topicFocus?: string;
}

export interface PipelineApiClientInterface {
  fetchRunList(
    params: RunListQueryParams,
  ): Promise<readonly PipelineRunSummary[]>;

  fetchRunDetail(pipelineRunId: string): Promise<PipelineRunDetail>;

  triggerRun(command: TriggerRunCommand): Promise<PipelineRunDetail>;

  pauseRun(pipelineRunId: string): Promise<void>;

  resumeRun(pipelineRunId: string): Promise<void>;
}

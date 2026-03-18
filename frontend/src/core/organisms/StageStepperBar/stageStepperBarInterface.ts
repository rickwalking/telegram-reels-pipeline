import type { StageStepStatus } from "@/core/molecules/StageStep/stageStepInterface";

export interface StageStepData {
  readonly stageName: string;
  readonly status: StageStepStatus;
  readonly durationSeconds?: number;
}

export interface StageStepperBarProps {
  readonly stages: readonly StageStepData[];
  readonly activeStageIndex: number;
  readonly onStageClick: (stageIndex: number) => void;
}

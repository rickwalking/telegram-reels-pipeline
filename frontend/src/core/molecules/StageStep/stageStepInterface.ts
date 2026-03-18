export type StageStepStatus =
  | "pending"
  | "active"
  | "completed"
  | "failed"
  | "paused";

export interface StageStepProps {
  readonly stageName: string;
  readonly status: StageStepStatus;
  readonly durationSeconds?: number;
  readonly isActive?: boolean;
  readonly onClick: () => void;
}

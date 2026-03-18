export interface StageBoundaryData {
  readonly stageName: string;
  readonly startedAt: string;
  readonly durationSeconds: number;
  readonly eventIndex: number;
}

export interface StageBoundaryMarkerProps {
  readonly boundary: StageBoundaryData;
}

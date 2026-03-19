import { useCallback, useState, startTransition } from "react";
import { useParams } from "@tanstack/react-router";
import { runDetailRoute } from "@/app/routes/routeTree";
import { usePipelineRunDetail } from "@/app/hooks/usePipelineRunDetail";
import { useServices } from "@/app/hooks/useServices";
import { StageStepperBar } from "@/core/organisms/StageStepperBar/StageStepperBar";
import { DocumentCarousel } from "@/core/organisms/DocumentCarousel/DocumentCarousel";
import { RunDetailHeader } from "./RunDetailHeader";
import type { StageStepData } from "@/core/organisms/StageStepperBar/stageStepperBarInterface";
import type { StatusBadgeVariant } from "@/core/atoms/statusBadge/statusBadgeInterface";
import type { StageStepStatus } from "@/core/molecules/StageStep/stageStepInterface";

const PIPELINE_STAGES: readonly string[] = [
  "Router", "Research", "Transcript", "Content", "Layout", "FFmpeg", "Assembly",
];

const VALID_STATUSES: ReadonlySet<string> = new Set([
  "pending", "active", "completed", "failed", "paused",
]);

function mapToStatusVariant(rawStatus: string): StatusBadgeVariant {
  if (VALID_STATUSES.has(rawStatus)) return rawStatus as StatusBadgeVariant;
  return "pending";
}

function deriveStageSteps(
  completedStages: readonly string[],
  currentStage: string,
  executionStatus: string,
): readonly StageStepData[] {
  const completedSet = new Set(completedStages.map((stageName) => stageName.toLowerCase()));

  return PIPELINE_STAGES.map((stageName): StageStepData => {
    const lowerName = stageName.toLowerCase();
    if (completedSet.has(lowerName)) {
      return { stageName, status: "completed" as StageStepStatus };
    }
    if (currentStage.toLowerCase() === lowerName) {
      return { stageName, status: mapToStatusVariant(executionStatus) as StageStepStatus };
    }
    return { stageName, status: "pending" as StageStepStatus };
  });
}

export function RunDetailContent() {
  const { runId } = useParams({ from: runDetailRoute.id });
  const { data: runDetail } = usePipelineRunDetail(runId);
  const { pipelineApiClient } = useServices();
  const [activeStageIndex, setActiveStageIndex] = useState(0);
  const [activeArtifactTab, setActiveArtifactTab] = useState("");

  const stageSteps = deriveStageSteps(
    runDetail.completedStages,
    runDetail.currentStage,
    runDetail.executionStatus,
  );

  const handleStageClick = useCallback((stageIndex: number) => {
    startTransition(() => setActiveStageIndex(stageIndex));
  }, []);

  const handleTabChange = useCallback((tabName: string) => {
    startTransition(() => setActiveArtifactTab(tabName));
  }, []);

  const handlePause = useCallback(async () => {
    await pipelineApiClient.pauseRun(runId);
  }, [pipelineApiClient, runId]);

  const handleResume = useCallback(async () => {
    await pipelineApiClient.resumeRun(runId);
  }, [pipelineApiClient, runId]);

  return (
    <div className="flex flex-col h-[calc(100vh-3.5rem)]">
      <RunDetailHeader
        pipelineRunId={runId}
        executionStatus={mapToStatusVariant(runDetail.executionStatus)}
        onPause={handlePause}
        onResume={handleResume}
      />
      <div className="border-b border-border">
        <StageStepperBar
          stages={stageSteps}
          activeStageIndex={activeStageIndex}
          onStageClick={handleStageClick}
        />
      </div>
      <div className="flex-1 overflow-y-auto p-4">
        <DocumentCarousel
          artifacts={[]}
          activeTab={activeArtifactTab}
          onTabChange={handleTabChange}
        />
      </div>
    </div>
  );
}

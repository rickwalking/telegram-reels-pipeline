import { useCallback } from "react";
import { cn } from "@/lib/utils";
import { StageStep } from "@/core/molecules/StageStep/StageStep";
import type { StageStepperBarProps } from "./stageStepperBarInterface";

export function StageStepperBar({
  stages,
  activeStageIndex,
  onStageClick,
}: StageStepperBarProps) {
  const handleStageClick = useCallback(
    (stageIndex: number) => () => {
      onStageClick(stageIndex);
    },
    [onStageClick],
  );

  return (
    <nav aria-label="Pipeline stages">
      <ol
        data-testid="stage-stepper-bar"
        className={cn(
          "flex list-none gap-1 p-2",
          "flex-col md:flex-row md:overflow-x-auto",
        )}
      >
        {stages.map((stageData, stageIndex) => (
          <li
            key={stageData.stageName}
            aria-current={stageIndex === activeStageIndex ? "step" : undefined}
          >
            <StageStep
              stageName={stageData.stageName}
              status={stageData.status}
              durationSeconds={stageData.durationSeconds}
              isActive={stageIndex === activeStageIndex}
              onClick={handleStageClick(stageIndex)}
            />
          </li>
        ))}
      </ol>
    </nav>
  );
}

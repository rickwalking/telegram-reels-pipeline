import type { PipelineEventItem } from "@/services/interfaces/pipelineEventApiInterface";
import type { StageBoundaryData } from "@/core/atoms/StageBoundaryMarker/stageBoundaryMarkerInterface";

/**
 * Derives stage boundaries from a sequential list of pipeline events.
 * A new boundary is created each time the stage field changes.
 */
export function deriveStageBoundaries(
  eventItems: readonly PipelineEventItem[],
): StageBoundaryData[] {
  const boundaries: StageBoundaryData[] = [];
  let currentStageName: string | null = null;
  let stageStartTimestamp: string | null = null;
  let stageStartIndex = 0;

  for (let eventIndex = 0; eventIndex < eventItems.length; eventIndex++) {
    const eventItem = eventItems[eventIndex];
    if (eventItem === undefined) continue;
    if (eventItem.stage === null) continue;
    if (eventItem.stage === currentStageName) continue;

    if (currentStageName !== null && stageStartTimestamp !== null) {
      const durationSeconds = computeDurationSeconds(
        stageStartTimestamp,
        eventItem.timestamp,
      );
      boundaries.push({
        stageName: currentStageName,
        startedAt: stageStartTimestamp,
        durationSeconds,
        eventIndex: stageStartIndex,
      });
    }

    currentStageName = eventItem.stage;
    stageStartTimestamp = eventItem.timestamp;
    stageStartIndex = eventIndex;
  }

  if (currentStageName !== null && stageStartTimestamp !== null) {
    const lastTimestamp =
      eventItems[eventItems.length - 1]?.timestamp ?? stageStartTimestamp;
    const durationSeconds = computeDurationSeconds(
      stageStartTimestamp,
      lastTimestamp,
    );
    boundaries.push({
      stageName: currentStageName,
      startedAt: stageStartTimestamp,
      durationSeconds,
      eventIndex: stageStartIndex,
    });
  }

  return boundaries;
}

function computeDurationSeconds(
  startIso: string,
  endIso: string,
): number {
  const startMs = new Date(startIso).getTime();
  const endMs = new Date(endIso).getTime();
  return Math.max(0, (endMs - startMs) / 1000);
}

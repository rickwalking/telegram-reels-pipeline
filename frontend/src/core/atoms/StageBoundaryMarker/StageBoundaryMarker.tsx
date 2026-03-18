import { formatDuration } from "@/utils/formatDuration";
import type { StageBoundaryMarkerProps } from "./stageBoundaryMarkerInterface";

export function StageBoundaryMarker({ boundary }: StageBoundaryMarkerProps) {
  const isoDuration = `PT${Math.round(boundary.durationSeconds)}S`;

  return (
    <div className="flex items-center gap-2 py-1 select-none" aria-hidden="true">
      <div className="flex-1 h-px bg-border" />
      <span className="text-[0.7rem] font-semibold uppercase tracking-wider text-muted-foreground">
        {boundary.stageName}
      </span>
      <time
        className="text-[0.7rem] tabular-nums text-muted-foreground/70"
        dateTime={isoDuration}
      >
        {formatDuration(boundary.durationSeconds)}
      </time>
      <div className="flex-1 h-px bg-border" />
    </div>
  );
}

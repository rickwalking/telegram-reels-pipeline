import { cn } from "@/lib/utils";
import { useReducedMotion } from "@/core/hooks/useReducedMotion";
import { formatDuration } from "@/utils/formatDuration";
import type { StageStepProps, StageStepStatus } from "./stageStepInterface";

const STATUS_CIRCLE_COLORS: Readonly<Record<StageStepStatus, string>> = {
  pending: "bg-muted-foreground/40",
  active: "bg-blue-500",
  completed: "bg-green-500",
  failed: "bg-red-500",
  paused: "bg-amber-500",
};

const STATUS_LABELS: Readonly<Record<StageStepStatus, string>> = {
  pending: "Pending",
  active: "Active",
  completed: "Completed",
  failed: "Failed",
  paused: "Paused",
};

export function StageStep({
  stageName,
  status,
  durationSeconds,
  isActive = false,
  onClick,
}: StageStepProps) {
  const prefersReducedMotion = useReducedMotion();
  const shouldPulse = status === "active" && isActive && !prefersReducedMotion;

  return (
    <button
      type="button"
      data-testid="stage-step"
      data-status={status}
      className={cn(
        "flex items-center gap-2.5 rounded-md px-3 py-2 text-sm cursor-pointer",
        "min-h-[44px] min-w-[44px] touch-action-manipulation",
        "hover:bg-muted focus-visible:ring-2 focus-visible:ring-ring focus-visible:outline-none",
        isActive ? "bg-muted font-medium" : "bg-transparent",
      )}
      aria-expanded={isActive}
      aria-label={`${stageName} stage, status: ${STATUS_LABELS[status]}`}
      onClick={onClick}
    >
      <span
        data-testid="status-circle"
        className={cn(
          "size-3 shrink-0 rounded-full",
          STATUS_CIRCLE_COLORS[status],
          shouldPulse ? "animate-pulse" : "",
        )}
        aria-hidden="true"
      />
      <span className="truncate">{stageName}</span>
      {durationSeconds !== undefined ? (
        <span
          data-testid="stage-duration"
          className="ml-auto text-xs text-muted-foreground"
          style={{ fontVariantNumeric: "tabular-nums" }}
        >
          {formatDuration(durationSeconds)}
        </span>
      ) : null}
    </button>
  );
}

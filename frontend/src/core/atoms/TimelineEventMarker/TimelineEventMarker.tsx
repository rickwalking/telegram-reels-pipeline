import { cn } from "@/lib/utils";
import { getEventColorClass, getEventRingClass } from "@/utils/eventColorMap";
import type { TimelineEventMarkerProps } from "./timelineEventMarkerInterface";

function extractShortName(eventName: string): string {
  return eventName.split(".").pop() ?? eventName;
}

export function TimelineEventMarker({
  event,
  isSelected,
  onSelect,
}: TimelineEventMarkerProps) {
  const colorClass = getEventColorClass(event.eventName);
  const ringClass = getEventRingClass(event.eventName);
  const shortLabel = extractShortName(event.eventName);

  return (
    <button
      type="button"
      className={cn(
        "inline-flex items-center gap-1.5 min-w-11 min-h-11 px-2.5 py-1.5",
        "rounded-lg border-2 border-transparent text-xs",
        "transition-colors duration-150 cursor-pointer",
        "hover:bg-muted/50 focus-visible:outline-none",
        isSelected
          ? `border-current ring-2 ${ringClass} bg-muted/30`
          : "focus-visible:ring-2 focus-visible:ring-ring",
      )}
      aria-label={`Event: ${event.eventName} at ${event.timestamp}`}
      aria-pressed={isSelected}
      onClick={() => onSelect(event.eventId)}
      title={event.eventName}
    >
      <span
        className={cn("block size-2.5 rounded-full shrink-0", colorClass)}
        aria-hidden="true"
      />
      <span className="truncate max-w-[120px]">{shortLabel}</span>
    </button>
  );
}

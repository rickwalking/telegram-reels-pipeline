/** Maps event names to Tailwind-compatible color tokens for DVR timeline markers. */

const EVENT_COLOR_MAP: Readonly<Record<string, string>> = {
  "pipeline.stage_entered": "bg-blue-500",
  "pipeline.stage_completed": "bg-green-500",
  "pipeline.stage_failed": "bg-red-500",
  "pipeline.qa_pass": "bg-green-500",
  "pipeline.qa_rework": "bg-amber-500",
  "pipeline.qa_fail": "bg-red-500",
  "pipeline.recovery": "bg-purple-500",
  "pipeline.started": "bg-indigo-500",
  "pipeline.completed": "bg-green-500",
};

const DEFAULT_EVENT_COLOR = "bg-slate-400";

export function getEventColorClass(eventName: string): string {
  return EVENT_COLOR_MAP[eventName] ?? DEFAULT_EVENT_COLOR;
}

/** Foreground ring color for focus states. */
const EVENT_RING_MAP: Readonly<Record<string, string>> = {
  "pipeline.stage_entered": "ring-blue-500",
  "pipeline.stage_completed": "ring-green-500",
  "pipeline.stage_failed": "ring-red-500",
  "pipeline.qa_pass": "ring-green-500",
  "pipeline.qa_rework": "ring-amber-500",
  "pipeline.qa_fail": "ring-red-500",
  "pipeline.recovery": "ring-purple-500",
  "pipeline.started": "ring-indigo-500",
  "pipeline.completed": "ring-green-500",
};

const DEFAULT_RING_COLOR = "ring-slate-400";

export function getEventRingClass(eventName: string): string {
  return EVENT_RING_MAP[eventName] ?? DEFAULT_RING_COLOR;
}

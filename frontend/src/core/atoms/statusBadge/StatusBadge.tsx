import { cn } from "@/lib/utils";
import type { StatusBadgeProps, StatusBadgeVariant } from "./statusBadgeInterface";
import { STATUS_BADGE_LABELS } from "./statusBadgeInterface";

const VARIANT_CLASS_MAP: Readonly<Record<StatusBadgeVariant, string>> = {
  pending:
    "bg-status-pending text-status-pending-foreground",
  active:
    "bg-status-active text-status-active-foreground",
  completed:
    "bg-status-completed text-status-completed-foreground",
  failed:
    "bg-status-failed text-status-failed-foreground",
  paused:
    "bg-status-paused text-status-paused-foreground",
};

export function StatusBadge({ variant, label, className }: StatusBadgeProps) {
  const displayLabel = label ?? STATUS_BADGE_LABELS[variant];
  const variantClasses = VARIANT_CLASS_MAP[variant];

  return (
    <span
      data-testid="status-badge"
      data-variant={variant}
      className={cn(
        "inline-flex items-center rounded-md px-2.5 py-0.5 text-xs font-medium",
        variantClasses,
        className,
      )}
    >
      {displayLabel}
    </span>
  );
}

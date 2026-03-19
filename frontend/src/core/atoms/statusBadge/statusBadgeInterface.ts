export type StatusBadgeVariant =
  | "pending"
  | "active"
  | "completed"
  | "failed"
  | "paused";

export interface StatusBadgeProps {
  readonly variant: StatusBadgeVariant;
  readonly label?: string;
  readonly className?: string;
}

export const STATUS_BADGE_LABELS: Readonly<
  Record<StatusBadgeVariant, string>
> = {
  pending: "Pending",
  active: "Active",
  completed: "Completed",
  failed: "Failed",
  paused: "Paused",
};

import { Link } from "@tanstack/react-router";
import { StatusBadge } from "@/core/atoms/statusBadge/StatusBadge";
import type { RunListItemProps } from "./runListItemInterface";

const TIMESTAMP_FORMAT_OPTIONS: Intl.DateTimeFormatOptions = {
  month: "short",
  day: "numeric",
  hour: "2-digit",
  minute: "2-digit",
};

function formatTimestamp(isoTimestamp: string): string {
  return new Intl.DateTimeFormat("en-US", TIMESTAMP_FORMAT_OPTIONS).format(
    new Date(isoTimestamp),
  );
}

export function RunListItem({
  pipelineRunId,
  youtubeUrl,
  executionStatus,
  createdAt,
  onPrefetch,
}: RunListItemProps) {
  return (
    <Link
      to="/runs/$runId"
      params={{ runId: pipelineRunId }}
      data-testid="run-list-item"
      className="flex items-center gap-3 rounded-lg border border-border px-4 py-3 hover:bg-muted focus-visible:ring-2 focus-visible:ring-ring focus-visible:outline-none min-h-[44px]"
      onPointerEnter={onPrefetch}
    >
      <StatusBadge variant={executionStatus} />
      <span className="flex-1 truncate text-sm" title={youtubeUrl}>
        {youtubeUrl}
      </span>
      <time
        dateTime={createdAt}
        className="shrink-0 text-xs text-muted-foreground"
        style={{ fontVariantNumeric: "tabular-nums" }}
      >
        {formatTimestamp(createdAt)}
      </time>
    </Link>
  );
}

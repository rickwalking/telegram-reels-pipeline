import { getEventColorClass } from "@/utils/eventColorMap";
import { JsonPayloadViewer } from "@/core/molecules/JsonPayloadViewer/JsonPayloadViewer";
import type { EventDetailPanelProps } from "./eventDetailPanelInterface";

export function EventDetailPanel({
  selectedEvent,
  onClose,
}: EventDetailPanelProps) {
  if (selectedEvent === null) {
    return (
      <aside
        className="flex items-center justify-center h-full p-4 text-muted-foreground text-sm border-l border-border"
        aria-label="Event detail panel"
      >
        Select an event to view details
      </aside>
    );
  }

  const dotColorClass = getEventColorClass(selectedEvent.eventName);

  return (
    <aside
      className="flex flex-col gap-4 p-4 h-full overflow-y-auto border-l border-border max-md:border-l-0 max-md:border-t max-md:max-h-[50vh]"
      aria-label="Event detail panel"
    >
      <div className="flex justify-between items-center">
        <div className="flex items-center gap-2">
          <span className={`block size-2.5 rounded-full ${dotColorClass}`} />
          <h3 className="text-base font-semibold m-0">
            {selectedEvent.eventName}
          </h3>
        </div>
        <button
          type="button"
          className="inline-flex items-center justify-center size-8 rounded-md bg-transparent text-muted-foreground hover:bg-muted cursor-pointer border-none"
          onClick={onClose}
          aria-label="Close detail panel"
        >
          X
        </button>
      </div>

      <dl className="flex flex-col gap-2 m-0">
        <MetaItem label="Event ID">
          <code className="font-mono text-sm text-foreground/80">
            {selectedEvent.eventId}
          </code>
          <CopyIdButton eventId={selectedEvent.eventId} />
        </MetaItem>
        <MetaItem label="Timestamp">
          <time dateTime={selectedEvent.timestamp}>
            {selectedEvent.timestamp}
          </time>
        </MetaItem>
        {selectedEvent.stage !== null ? (
          <MetaItem label="Stage">{selectedEvent.stage}</MetaItem>
        ) : null}
      </dl>

      <JsonPayloadViewer payload={selectedEvent.payload} />
    </aside>
  );
}

interface MetaItemProps {
  readonly label: string;
  readonly children: React.ReactNode;
}

function MetaItem({ label, children }: MetaItemProps) {
  return (
    <div className="flex flex-col gap-0.5">
      <dt className="text-[0.7rem] font-semibold uppercase tracking-wider text-muted-foreground">
        {label}
      </dt>
      <dd className="m-0 flex items-center gap-2 text-sm">{children}</dd>
    </div>
  );
}

interface CopyIdButtonProps {
  readonly eventId: string;
}

function CopyIdButton({ eventId }: CopyIdButtonProps) {
  return (
    <button
      type="button"
      className="inline-flex items-center px-2 py-0.5 text-xs rounded border border-border bg-background hover:bg-muted cursor-pointer"
      onClick={() => navigator.clipboard.writeText(eventId)}
      aria-label="Copy ID"
    >
      Copy ID
    </button>
  );
}

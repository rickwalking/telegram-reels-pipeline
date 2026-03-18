import { useState, useCallback } from "react";
import { JsonNode } from "./JsonNode";
import type { JsonPayloadViewerProps } from "./jsonPayloadViewerInterface";

const COPY_BUTTON_LABEL = "Copy JSON";
const COPIED_LABEL = "Copied!";
const COPY_RESET_MS = 1500;

export function JsonPayloadViewer({
  payload,
  initialCollapsed = false,
}: JsonPayloadViewerProps) {
  const [isCopied, setIsCopied] = useState(false);
  const jsonString = JSON.stringify(payload, null, 2);

  const handleCopy = useCallback(() => {
    navigator.clipboard.writeText(jsonString).then(() => {
      setIsCopied(true);
      setTimeout(() => setIsCopied(false), COPY_RESET_MS);
    });
  }, [jsonString]);

  return (
    <div className="rounded-lg border border-border overflow-hidden font-mono text-[0.8rem] leading-relaxed">
      <div className="flex justify-between items-center px-3 py-1.5 bg-muted border-b border-border">
        <span className="text-[0.7rem] font-semibold uppercase tracking-wider text-muted-foreground">
          Payload
        </span>
        <button
          type="button"
          className="inline-flex items-center px-2.5 py-1 text-xs rounded-md border border-border bg-background hover:bg-muted cursor-pointer"
          onClick={handleCopy}
          aria-label={isCopied ? COPIED_LABEL : COPY_BUTTON_LABEL}
        >
          {isCopied ? COPIED_LABEL : COPY_BUTTON_LABEL}
        </button>
      </div>
      <div className="px-3 py-2 overflow-x-auto" style={{ contentVisibility: "auto" }}>
        <JsonNode
          nodeValue={payload}
          depth={0}
          initialCollapsed={initialCollapsed}
        />
      </div>
    </div>
  );
}

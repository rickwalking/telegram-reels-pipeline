import { useCallback, useRef, useState } from "react";
import { cn } from "@/lib/utils";
import type { CopyButtonProps } from "./copyButtonInterface";

const RESET_DELAY_MS = 2000;
const COPIED_LABEL = "Copied!";

export function CopyButton({ content, label, variant = "default" }: CopyButtonProps) {
  const [isCopied, setIsCopied] = useState(false);
  const resetTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const handleClick = useCallback(async () => {
    if (resetTimerRef.current !== null) {
      clearTimeout(resetTimerRef.current);
    }
    await navigator.clipboard.writeText(content);
    setIsCopied(true);
    resetTimerRef.current = setTimeout(() => setIsCopied(false), RESET_DELAY_MS);
  }, [content]);

  const variantClasses = variant === "ghost"
    ? "hover:bg-muted"
    : "border border-border bg-background hover:bg-muted";

  return (
    <button
      type="button"
      data-testid="copy-button"
      className={cn(
        "inline-flex items-center gap-1.5 rounded-md px-2.5 py-1 text-xs font-medium cursor-pointer",
        "focus-visible:ring-2 focus-visible:ring-ring focus-visible:outline-none",
        "min-h-[44px] min-w-[44px] touch-action-manipulation",
        variantClasses,
      )}
      onClick={handleClick}
      aria-label={isCopied ? COPIED_LABEL : label}
    >
      {isCopied ? (
        <svg
          aria-hidden="true"
          className="size-3.5"
          fill="none"
          viewBox="0 0 24 24"
          stroke="currentColor"
          strokeWidth={2}
        >
          <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
        </svg>
      ) : null}
      <span aria-live="polite">{isCopied ? COPIED_LABEL : label}</span>
    </button>
  );
}

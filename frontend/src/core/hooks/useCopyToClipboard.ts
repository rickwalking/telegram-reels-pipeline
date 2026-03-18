import { useCallback, useRef, useState } from "react";

interface CopyToClipboardState {
  readonly copiedText: string | null;
  readonly isCopied: boolean;
  readonly errorMessage: string | null;
}

interface CopyToClipboardResult {
  readonly state: CopyToClipboardState;
  readonly copyToClipboard: (text: string) => Promise<void>;
  readonly resetCopyState: () => void;
}

const INITIAL_STATE: CopyToClipboardState = {
  copiedText: null,
  isCopied: false,
  errorMessage: null,
};

const RESET_DELAY_MS = 2000;

/**
 * Hook for copying text to the clipboard with
 * success/error state tracking and auto-reset.
 */
export function useCopyToClipboard(): CopyToClipboardResult {
  const [state, setState] = useState<CopyToClipboardState>(INITIAL_STATE);
  const timeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const resetCopyState = useCallback(() => {
    setState(INITIAL_STATE);
  }, []);

  const copyToClipboard = useCallback(async (text: string): Promise<void> => {
    if (timeoutRef.current !== null) {
      clearTimeout(timeoutRef.current);
    }

    try {
      await navigator.clipboard.writeText(text);
      setState({ copiedText: text, isCopied: true, errorMessage: null });
      timeoutRef.current = setTimeout(resetCopyState, RESET_DELAY_MS);
    } catch (clipboardError: unknown) {
      const message = clipboardError instanceof Error
        ? clipboardError.message
        : "Failed to copy to clipboard";
      setState({ copiedText: null, isCopied: false, errorMessage: message });
    }
  }, [resetCopyState]);

  return { state, copyToClipboard, resetCopyState };
}

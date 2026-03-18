import { useEffect, useRef } from "react";

/**
 * Runs a callback exactly once on mount, safe in React StrictMode.
 * Returns optional cleanup function from the callback.
 */
export function useMountEffect(callback: () => void | (() => void)): void {
  const hasRun = useRef(false);

  useEffect(() => {
    if (hasRun.current) return;
    hasRun.current = true;
    return callback();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);
}

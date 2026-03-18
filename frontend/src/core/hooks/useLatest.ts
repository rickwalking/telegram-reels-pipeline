import { useRef } from "react";

/**
 * Returns a ref that always points to the latest value.
 * Useful in callbacks/effects that need the latest state
 * without re-subscribing.
 */
export function useLatest<T>(value: T): Readonly<{ current: T }> {
  const ref = useRef(value);
  ref.current = value;
  return ref;
}

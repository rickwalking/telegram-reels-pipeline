import { useSyncExternalStore } from "react";

const REDUCED_MOTION_QUERY = "(prefers-reduced-motion: reduce)";

function getServerSnapshot(): boolean {
  return false;
}

function getClientSnapshot(): boolean {
  return window.matchMedia(REDUCED_MOTION_QUERY).matches;
}

function subscribeToMotionPreference(onStoreChange: () => void): () => void {
  const mediaQuery = window.matchMedia(REDUCED_MOTION_QUERY);
  mediaQuery.addEventListener("change", onStoreChange);
  return () => mediaQuery.removeEventListener("change", onStoreChange);
}

/**
 * Returns true when the user has requested reduced motion
 * in their OS accessibility settings.
 */
export function useReducedMotion(): boolean {
  return useSyncExternalStore(
    subscribeToMotionPreference,
    getClientSnapshot,
    getServerSnapshot,
  );
}

import { useSyncExternalStore } from "react";

type BreakpointName = "mobile" | "tablet" | "desktop" | "wide";

interface BreakpointResult {
  readonly breakpoint: BreakpointName;
  readonly isMobile: boolean;
  readonly isTablet: boolean;
  readonly isDesktop: boolean;
  readonly isWide: boolean;
}

const BREAKPOINT_MOBILE_MAX = 639;
const BREAKPOINT_TABLET_MAX = 1023;
const BREAKPOINT_DESKTOP_MAX = 1279;

function resolveBreakpoint(width: number): BreakpointName {
  if (width <= BREAKPOINT_MOBILE_MAX) return "mobile";
  if (width <= BREAKPOINT_TABLET_MAX) return "tablet";
  if (width <= BREAKPOINT_DESKTOP_MAX) return "desktop";
  return "wide";
}

function getServerSnapshot(): BreakpointName {
  return "desktop";
}

function getClientSnapshot(): BreakpointName {
  return resolveBreakpoint(window.innerWidth);
}

function subscribeToResize(onStoreChange: () => void): () => void {
  window.addEventListener("resize", onStoreChange);
  return () => window.removeEventListener("resize", onStoreChange);
}

/**
 * Returns the current responsive breakpoint name and
 * boolean helpers. Updates reactively on window resize.
 */
export function useBreakpoint(): BreakpointResult {
  const breakpoint = useSyncExternalStore(
    subscribeToResize,
    getClientSnapshot,
    getServerSnapshot,
  );

  return {
    breakpoint,
    isMobile: breakpoint === "mobile",
    isTablet: breakpoint === "tablet",
    isDesktop: breakpoint === "desktop",
    isWide: breakpoint === "wide",
  };
}

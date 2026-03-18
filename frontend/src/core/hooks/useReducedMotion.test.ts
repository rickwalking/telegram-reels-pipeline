import { renderHook } from "@testing-library/react";
import { describe, expect, it, vi, beforeEach, afterEach } from "vitest";
import { useReducedMotion } from "./useReducedMotion";

describe("useReducedMotion", () => {
  let matchMediaMock: ReturnType<typeof vi.fn>;
  const originalMatchMedia = window.matchMedia;

  beforeEach(() => {
    matchMediaMock = vi.fn().mockReturnValue({
      matches: false,
      addEventListener: vi.fn(),
      removeEventListener: vi.fn(),
    });
    Object.defineProperty(window, "matchMedia", {
      writable: true,
      configurable: true,
      value: matchMediaMock,
    });
  });

  afterEach(() => {
    Object.defineProperty(window, "matchMedia", {
      writable: true,
      configurable: true,
      value: originalMatchMedia,
    });
  });

  it("returns false when motion is not reduced", () => {
    // Arrange & Act
    const { result } = renderHook(() => useReducedMotion());

    // Assert
    expect(result.current).toBe(false);
  });

  it("returns true when reduced motion is preferred", () => {
    // Arrange
    matchMediaMock.mockReturnValue({
      matches: true,
      addEventListener: vi.fn(),
      removeEventListener: vi.fn(),
    });

    // Act
    const { result } = renderHook(() => useReducedMotion());

    // Assert
    expect(result.current).toBe(true);
  });

  it("queries the correct media query string", () => {
    // Arrange & Act
    renderHook(() => useReducedMotion());

    // Assert
    expect(matchMediaMock).toHaveBeenCalledWith(
      "(prefers-reduced-motion: reduce)",
    );
  });

  it("subscribes and unsubscribes to change events", () => {
    // Arrange
    const addListener = vi.fn();
    const removeListener = vi.fn();
    matchMediaMock.mockReturnValue({
      matches: false,
      addEventListener: addListener,
      removeEventListener: removeListener,
    });

    // Act
    const { unmount } = renderHook(() => useReducedMotion());
    unmount();

    // Assert
    expect(addListener).toHaveBeenCalledWith("change", expect.any(Function));
    expect(removeListener).toHaveBeenCalledWith(
      "change",
      expect.any(Function),
    );
  });
});

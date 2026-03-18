import { renderHook } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { useMountEffect } from "./useMountEffect";

describe("useMountEffect", () => {
  it("calls callback exactly once on mount", () => {
    // Arrange
    const callback = vi.fn();

    // Act
    const { rerender } = renderHook(() => useMountEffect(callback));
    rerender();
    rerender();

    // Assert
    expect(callback).toHaveBeenCalledTimes(1);
  });

  it("calls cleanup function on unmount", () => {
    // Arrange
    const cleanup = vi.fn();
    const callback = vi.fn(() => cleanup);

    // Act
    const { unmount } = renderHook(() => useMountEffect(callback));
    unmount();

    // Assert
    expect(cleanup).toHaveBeenCalledTimes(1);
  });

  it("does not call callback again after rerender", () => {
    // Arrange
    const callback = vi.fn();

    // Act
    const { rerender } = renderHook(() => useMountEffect(callback));
    rerender();
    rerender();
    rerender();

    // Assert
    expect(callback).toHaveBeenCalledTimes(1);
  });
});

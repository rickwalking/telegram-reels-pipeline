import { renderHook } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { useLatest } from "./useLatest";

describe("useLatest", () => {
  it("returns a ref with the initial value", () => {
    // Arrange & Act
    const { result } = renderHook(() => useLatest("initial"));

    // Assert
    expect(result.current.current).toBe("initial");
  });

  it("updates the ref when value changes", () => {
    // Arrange
    const { result, rerender } = renderHook(
      ({ value }: { value: string }) => useLatest(value),
      { initialProps: { value: "first" } },
    );

    // Act
    rerender({ value: "second" });

    // Assert
    expect(result.current.current).toBe("second");
  });

  it("maintains referential identity of the ref object", () => {
    // Arrange
    const { result, rerender } = renderHook(
      ({ value }: { value: number }) => useLatest(value),
      { initialProps: { value: 1 } },
    );
    const firstRef = result.current;

    // Act
    rerender({ value: 2 });

    // Assert
    expect(result.current).toBe(firstRef);
  });
});

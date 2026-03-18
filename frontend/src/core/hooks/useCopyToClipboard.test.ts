import { act, renderHook } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { useCopyToClipboard } from "./useCopyToClipboard";

describe("useCopyToClipboard", () => {
  beforeEach(() => {
    vi.useFakeTimers();
  });

  it("starts with empty initial state", () => {
    // Arrange & Act
    const { result } = renderHook(() => useCopyToClipboard());

    // Assert
    expect(result.current.state.copiedText).toBeNull();
    expect(result.current.state.isCopied).toBe(false);
    expect(result.current.state.errorMessage).toBeNull();
  });

  it("copies text successfully", async () => {
    // Arrange
    const writeTextMock = vi.fn().mockResolvedValue(undefined);
    Object.assign(navigator, {
      clipboard: { writeText: writeTextMock },
    });
    const { result } = renderHook(() => useCopyToClipboard());

    // Act
    await act(async () => {
      await result.current.copyToClipboard("hello");
    });

    // Assert
    expect(writeTextMock).toHaveBeenCalledWith("hello");
    expect(result.current.state.copiedText).toBe("hello");
    expect(result.current.state.isCopied).toBe(true);
    expect(result.current.state.errorMessage).toBeNull();
  });

  it("handles clipboard write failure", async () => {
    // Arrange
    const writeTextMock = vi.fn().mockRejectedValue(new Error("Denied"));
    Object.assign(navigator, {
      clipboard: { writeText: writeTextMock },
    });
    const { result } = renderHook(() => useCopyToClipboard());

    // Act
    await act(async () => {
      await result.current.copyToClipboard("hello");
    });

    // Assert
    expect(result.current.state.isCopied).toBe(false);
    expect(result.current.state.errorMessage).toBe("Denied");
  });

  it("auto-resets after delay", async () => {
    // Arrange
    const writeTextMock = vi.fn().mockResolvedValue(undefined);
    Object.assign(navigator, {
      clipboard: { writeText: writeTextMock },
    });
    const { result } = renderHook(() => useCopyToClipboard());

    // Act
    await act(async () => {
      await result.current.copyToClipboard("hello");
    });
    act(() => {
      vi.advanceTimersByTime(2000);
    });

    // Assert
    expect(result.current.state.isCopied).toBe(false);
    expect(result.current.state.copiedText).toBeNull();
  });

  it("resets state manually", async () => {
    // Arrange
    const writeTextMock = vi.fn().mockResolvedValue(undefined);
    Object.assign(navigator, {
      clipboard: { writeText: writeTextMock },
    });
    const { result } = renderHook(() => useCopyToClipboard());
    await act(async () => {
      await result.current.copyToClipboard("hello");
    });

    // Act
    act(() => {
      result.current.resetCopyState();
    });

    // Assert
    expect(result.current.state.isCopied).toBe(false);
    expect(result.current.state.copiedText).toBeNull();
  });
});

import { renderHook, act } from "@testing-library/react";
import { describe, expect, it, vi, beforeEach, afterEach } from "vitest";
import { useBreakpoint } from "./useBreakpoint";

describe("useBreakpoint", () => {
  const originalInnerWidth = window.innerWidth;

  beforeEach(() => {
    Object.defineProperty(window, "innerWidth", {
      writable: true,
      configurable: true,
      value: 1024,
    });
  });

  afterEach(() => {
    Object.defineProperty(window, "innerWidth", {
      writable: true,
      configurable: true,
      value: originalInnerWidth,
    });
  });

  it("returns desktop for default 1024px width", () => {
    // Arrange & Act
    const { result } = renderHook(() => useBreakpoint());

    // Assert
    expect(result.current.breakpoint).toBe("desktop");
    expect(result.current.isDesktop).toBe(true);
  });

  it("returns mobile for narrow viewport", () => {
    // Arrange
    Object.defineProperty(window, "innerWidth", { value: 400 });

    // Act
    const { result } = renderHook(() => useBreakpoint());

    // Assert
    expect(result.current.breakpoint).toBe("mobile");
    expect(result.current.isMobile).toBe(true);
  });

  it("returns tablet for medium viewport", () => {
    // Arrange
    Object.defineProperty(window, "innerWidth", { value: 768 });

    // Act
    const { result } = renderHook(() => useBreakpoint());

    // Assert
    expect(result.current.breakpoint).toBe("tablet");
    expect(result.current.isTablet).toBe(true);
  });

  it("returns wide for large viewport", () => {
    // Arrange
    Object.defineProperty(window, "innerWidth", { value: 1440 });

    // Act
    const { result } = renderHook(() => useBreakpoint());

    // Assert
    expect(result.current.breakpoint).toBe("wide");
    expect(result.current.isWide).toBe(true);
  });

  it("updates on window resize", () => {
    // Arrange
    const addEventSpy = vi.spyOn(window, "addEventListener");
    const { result } = renderHook(() => useBreakpoint());
    expect(result.current.isDesktop).toBe(true);

    // Act
    Object.defineProperty(window, "innerWidth", { value: 400 });
    act(() => {
      window.dispatchEvent(new Event("resize"));
    });

    // Assert
    expect(result.current.isMobile).toBe(true);
    expect(addEventSpy).toHaveBeenCalledWith("resize", expect.any(Function));
    addEventSpy.mockRestore();
  });
});

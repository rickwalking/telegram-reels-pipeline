import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { StageBoundaryMarker } from "./StageBoundaryMarker";
import type { StageBoundaryData } from "./stageBoundaryMarkerInterface";

const SAMPLE_BOUNDARY: StageBoundaryData = {
  stageName: "ROUTER",
  startedAt: "2026-03-18T10:00:00Z",
  durationSeconds: 42.5,
  eventIndex: 0,
};

describe("StageBoundaryMarker", () => {
  it("renders with aria-hidden true", () => {
    // Arrange & Act
    const { container } = render(
      <StageBoundaryMarker boundary={SAMPLE_BOUNDARY} />,
    );
    const rootElement = container.firstElementChild;

    // Assert
    expect(rootElement).toHaveAttribute("aria-hidden", "true");
  });

  it("displays stage name", () => {
    // Arrange & Act
    render(<StageBoundaryMarker boundary={SAMPLE_BOUNDARY} />);

    // Assert
    expect(screen.getByText("ROUTER")).toBeInTheDocument();
  });

  it("renders duration in a time element with ISO datetime", () => {
    // Arrange & Act
    render(<StageBoundaryMarker boundary={SAMPLE_BOUNDARY} />);
    const timeElement = screen.getByText("42.5s");

    // Assert
    expect(timeElement.tagName).toBe("TIME");
    expect(timeElement).toHaveAttribute("dateTime", "PT43S");
  });

  it("formats durations over 60s with minutes", () => {
    // Arrange
    const longBoundary: StageBoundaryData = {
      ...SAMPLE_BOUNDARY,
      durationSeconds: 125,
    };

    // Act
    render(<StageBoundaryMarker boundary={longBoundary} />);

    // Assert
    expect(screen.getByText("2m 5s")).toBeInTheDocument();
  });

  it("uses tabular-nums class for duration", () => {
    // Arrange & Act
    render(<StageBoundaryMarker boundary={SAMPLE_BOUNDARY} />);
    const timeElement = screen.getByText("42.5s");

    // Assert
    expect(timeElement.className).toContain("tabular-nums");
  });
});

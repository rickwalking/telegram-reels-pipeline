import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi, beforeEach } from "vitest";
import { DocumentCarousel } from "./DocumentCarousel";
import type { ArtifactEntry } from "./documentCarouselInterface";

beforeEach(() => {
  Object.assign(navigator, {
    clipboard: { writeText: vi.fn().mockResolvedValue(undefined) },
  });
});

const JSON_ARTIFACT: ArtifactEntry = {
  artifactName: "router-output",
  contentType: "json",
  payload: { stage: "router", status: "completed" },
};

const MARKDOWN_ARTIFACT: ArtifactEntry = {
  artifactName: "transcript",
  contentType: "markdown",
  payload: "# Transcript\n\nHello world",
};

const BINARY_ARTIFACT: ArtifactEntry = {
  artifactName: "final-reel",
  contentType: "binary",
  payload: "",
  downloadUrl: "/api/download/final-reel.mp4",
};

const ALL_ARTIFACTS: readonly ArtifactEntry[] = [
  JSON_ARTIFACT,
  MARKDOWN_ARTIFACT,
  BINARY_ARTIFACT,
];

describe("DocumentCarousel", () => {
  it("should render tabs for each artifact", () => {
    // Arrange & Act
    render(
      <DocumentCarousel
        artifacts={ALL_ARTIFACTS}
        activeTab="router-output"
        onTabChange={vi.fn()}
      />,
    );

    // Assert
    expect(screen.getByText("router-output")).toBeInTheDocument();
    expect(screen.getByText("transcript")).toBeInTheDocument();
    expect(screen.getByText("final-reel")).toBeInTheDocument();
  });

  it("should render empty state when no artifacts", () => {
    // Arrange & Act
    render(
      <DocumentCarousel artifacts={[]} activeTab="" onTabChange={vi.fn()} />,
    );

    // Assert
    expect(screen.getByTestId("document-carousel-empty")).toBeInTheDocument();
  });

  it("should render the carousel container", () => {
    // Arrange & Act
    render(
      <DocumentCarousel
        artifacts={[JSON_ARTIFACT]}
        activeTab="router-output"
        onTabChange={vi.fn()}
      />,
    );

    // Assert
    expect(screen.getByTestId("document-carousel")).toBeInTheDocument();
  });

  it("should call onTabChange when clicking a tab", async () => {
    // Arrange
    const handleTabChange = vi.fn();
    const user = userEvent.setup();
    render(
      <DocumentCarousel
        artifacts={ALL_ARTIFACTS}
        activeTab="router-output"
        onTabChange={handleTabChange}
      />,
    );

    // Act
    await user.click(screen.getByText("transcript"));

    // Assert
    expect(handleTabChange).toHaveBeenCalledWith("transcript");
  });
});

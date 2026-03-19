import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { RunListItem } from "./RunListItem";
import {
  RouterProvider,
  createMemoryHistory,
  createRootRoute,
  createRoute,
  createRouter,
  Outlet,
} from "@tanstack/react-router";

function renderWithRouter(component: React.ReactElement) {
  const rootRoute = createRootRoute({ component: () => <><Outlet />{component}</> });
  const runDetailRoute = createRoute({
    getParentRoute: () => rootRoute,
    path: "/runs/$runId",
    component: () => <div>Detail Page</div>,
  });
  const routeTree = rootRoute.addChildren([runDetailRoute]);
  const memoryHistory = createMemoryHistory({ initialEntries: ["/"] });
  const testRouter = createRouter({ routeTree, history: memoryHistory });
  return render(<RouterProvider router={testRouter} />);
}

describe("RunListItem", () => {
  const DEFAULT_PROPS = {
    pipelineRunId: "run-001",
    youtubeUrl: "https://www.youtube.com/watch?v=test123",
    executionStatus: "active" as const,
    createdAt: "2026-03-18T10:00:00Z",
    onPrefetch: vi.fn(),
  };

  it("should display the YouTube URL", async () => {
    // Arrange & Act
    renderWithRouter(<RunListItem {...DEFAULT_PROPS} />);

    // Assert
    await waitFor(() => {
      expect(screen.getByText(DEFAULT_PROPS.youtubeUrl)).toBeInTheDocument();
    });
  });

  it("should display a status badge", async () => {
    // Arrange & Act
    renderWithRouter(<RunListItem {...DEFAULT_PROPS} />);

    // Assert
    await waitFor(() => {
      expect(screen.getByTestId("status-badge")).toBeInTheDocument();
    });
  });

  it("should display a formatted timestamp", async () => {
    // Arrange & Act
    renderWithRouter(<RunListItem {...DEFAULT_PROPS} />);

    // Assert
    await waitFor(() => {
      const timeElement = screen.getByTestId("run-list-item").querySelector("time");
      expect(timeElement).toBeInTheDocument();
      expect(timeElement).toHaveAttribute("dateTime", DEFAULT_PROPS.createdAt);
    });
  });

  it("should link to the run detail page", async () => {
    // Arrange & Act
    renderWithRouter(<RunListItem {...DEFAULT_PROPS} />);

    // Assert
    await waitFor(() => {
      const linkElement = screen.getByTestId("run-list-item");
      expect(linkElement).toHaveAttribute("href", "/runs/run-001");
    });
  });

  it("should call onPrefetch on pointer enter", async () => {
    // Arrange
    const handlePrefetch = vi.fn();
    renderWithRouter(<RunListItem {...DEFAULT_PROPS} onPrefetch={handlePrefetch} />);

    // Act & Assert
    await waitFor(() => {
      const linkItem = screen.getByTestId("run-list-item");
      fireEvent.pointerEnter(linkItem);
      expect(handlePrefetch).toHaveBeenCalledOnce();
    });
  });

  it("should truncate long URLs with title tooltip", async () => {
    // Arrange & Act
    renderWithRouter(<RunListItem {...DEFAULT_PROPS} />);

    // Assert
    await waitFor(() => {
      const urlSpan = screen.getByText(DEFAULT_PROPS.youtubeUrl);
      expect(urlSpan).toHaveAttribute("title", DEFAULT_PROPS.youtubeUrl);
      expect(urlSpan.className).toContain("truncate");
    });
  });
});

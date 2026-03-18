import { render, screen, waitFor } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import {
  RouterProvider,
  createMemoryHistory,
  createRootRoute,
  createRoute,
  createRouter,
} from "@tanstack/react-router";
import { ServiceProvider } from "@/app/providers/ServiceProvider";
import type { ServiceRegistry } from "@/app/providers/ServiceProvider";
import { FakePipelineApiService } from "@/services/fakes/fakePipelineApiService";
import { FakePipelineEventApiService } from "@/services/fakes/fakePipelineEventApiService";
import { FakeSseClientService } from "@/services/fakes/fakeSseClientService";
import { FakeClipboardService } from "@/services/fakes/fakeClipboardService";
import { RunDetailPage } from "./RunDetailPage";

vi.mock("@/core/hooks/useReducedMotion", () => ({
  useReducedMotion: () => false,
}));

function createTestServices(): ServiceRegistry {
  return {
    pipelineApiClient: new FakePipelineApiService(),
    pipelineEventApi: new FakePipelineEventApiService(),
    sseClient: new FakeSseClientService(),
    clipboardService: new FakeClipboardService(),
  };
}

function renderRunDetail(pipelineRunId = "run-001") {
  const testServices = createTestServices();
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });

  const rootRoute = createRootRoute({});
  const detailRoute = createRoute({
    getParentRoute: () => rootRoute,
    path: "/runs/$runId",
    component: RunDetailPage,
  });
  const routeTree = rootRoute.addChildren([detailRoute]);
  const memoryHistory = createMemoryHistory({
    initialEntries: [`/runs/${pipelineRunId}`],
  });
  const testRouter = createRouter({ routeTree, history: memoryHistory });

  return render(
    <QueryClientProvider client={queryClient}>
      <ServiceProvider services={testServices}>
        <RouterProvider router={testRouter} />
      </ServiceProvider>
    </QueryClientProvider>,
  );
}

describe("RunDetailPage", () => {
  it("should render the run detail header after loading", async () => {
    // Arrange & Act
    renderRunDetail("run-001");

    // Assert
    await waitFor(() => {
      expect(screen.getByTestId("run-detail-header")).toBeInTheDocument();
    });
  });

  it("should render the stage stepper bar after loading", async () => {
    // Arrange & Act
    renderRunDetail("run-001");

    // Assert
    await waitFor(() => {
      expect(screen.getByTestId("stage-stepper-bar")).toBeInTheDocument();
    });
  });

  it("should display run ID in the header", async () => {
    // Arrange & Act
    renderRunDetail("run-001");

    // Assert
    await waitFor(() => {
      expect(screen.getByText("run-001")).toBeInTheDocument();
    });
  });
});

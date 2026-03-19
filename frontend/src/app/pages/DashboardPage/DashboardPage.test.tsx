import { render, screen, waitFor } from "@testing-library/react";
import { describe, expect, it } from "vitest";
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
import { DashboardPage } from "./DashboardPage";

function createTestServices(): ServiceRegistry {
  return {
    pipelineApiClient: new FakePipelineApiService(),
    pipelineEventApi: new FakePipelineEventApiService(),
    sseClient: new FakeSseClientService(),
    clipboardService: new FakeClipboardService(),
  };
}

function renderDashboard() {
  const testServices = createTestServices();
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  const rootRoute = createRootRoute({});
  const indexRoute = createRoute({
    getParentRoute: () => rootRoute,
    path: "/",
    component: DashboardPage,
  });
  const routeTree = rootRoute.addChildren([indexRoute]);
  const memoryHistory = createMemoryHistory({ initialEntries: ["/"] });
  const testRouter = createRouter({ routeTree, history: memoryHistory });

  return render(
    <QueryClientProvider client={queryClient}>
      <ServiceProvider services={testServices}>
        <RouterProvider router={testRouter} />
      </ServiceProvider>
    </QueryClientProvider>,
  );
}

describe("DashboardPage", () => {
  it("should render the page title", async () => {
    // Arrange & Act
    renderDashboard();

    // Assert
    await waitFor(() => {
      expect(screen.getByText("Pipeline Runs")).toBeInTheDocument();
    });
  });

  it("should render the trigger button", async () => {
    // Arrange & Act
    renderDashboard();

    // Assert
    await waitFor(() => {
      expect(screen.getByTestId("trigger-run-button")).toBeInTheDocument();
    });
  });

  it("should render run list after loading", async () => {
    // Arrange & Act
    renderDashboard();

    // Assert
    await waitFor(() => {
      expect(screen.getByTestId("run-list")).toBeInTheDocument();
    });
  });
});

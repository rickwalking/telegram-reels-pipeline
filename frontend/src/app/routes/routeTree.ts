import {
  createRootRoute,
  createRoute,
  createRouter,
} from "@tanstack/react-router";
import { RootLayout } from "@/app/routes/RootLayout";
import { DashboardPage } from "@/app/pages/DashboardPage/DashboardPage";
import { RunDetailPage } from "@/app/pages/RunDetailPage/RunDetailPage";
import { RunDvrPage } from "@/app/pages/RunDvrPage";
import { TriggerRunPage } from "@/app/pages/TriggerRunPage";

const rootRoute = createRootRoute({
  component: RootLayout,
});

const indexRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: "/",
  component: DashboardPage,
});

export const runDetailRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: "/runs/$runId",
  component: RunDetailPage,
});

export const runDvrRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: "/runs/$runId/dvr",
  component: RunDvrPage,
});

const triggerRoute = createRoute({
  getParentRoute: () => rootRoute,
  path: "/trigger",
  component: TriggerRunPage,
});

const routeTree = rootRoute.addChildren([
  indexRoute,
  runDetailRoute,
  runDvrRoute,
  triggerRoute,
]);

export const router = createRouter({ routeTree });

declare module "@tanstack/react-router" {
  interface Register {
    router: typeof router;
  }
}

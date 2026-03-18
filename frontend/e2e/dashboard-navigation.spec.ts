/**
 * E2E tests for Dashboard navigation, routing, and UI behavior.
 * Validates page loading, navigation between pages, browser history,
 * theme support, and Vite proxy functionality.
 */
import { test, expect } from "@playwright/test";

const BACKEND_API_BASE = "http://localhost:8000/api";
const FRONTEND_BASE = "http://localhost:5173";

/**
 * Helper: create a test run and return its ID.
 */
async function createTestRun(
  requestContext: { post: (url: string, options: { data: Record<string, string> }) => Promise<{ json: () => Promise<Record<string, string>> }> },
): Promise<string> {
  const uniqueVideoId = `nav_e2e_${Date.now()}_${Math.random().toString(36).slice(2, 8)}`;
  const createResponse = await requestContext.post(`${BACKEND_API_BASE}/runs`, {
    data: {
      youtube_url: `https://www.youtube.com/watch?v=${uniqueVideoId}`,
    },
  });
  const createdRun = await createResponse.json();
  return createdRun.pipeline_run_id;
}

test.describe("Dashboard Navigation — Page Loading", () => {
  test("should load dashboard at root path /", async ({ page }) => {
    // Act
    await page.goto("/");

    // Assert
    await expect(page).toHaveTitle(/Pipeline/i);
    await expect(
      page.getByRole("heading", { name: "Pipeline Runs" }),
    ).toBeVisible();
  });

  test("should display the Pipeline Dashboard header link", async ({
    page,
  }) => {
    // Act
    await page.goto("/");

    // Assert
    const headerLink = page.locator(
      'header a:has-text("Pipeline Dashboard")',
    );
    await expect(headerLink).toBeVisible();
  });

  test("should show trigger button on dashboard", async ({ page }) => {
    // Act
    await page.goto("/");

    // Assert
    const triggerButton = page.getByTestId("trigger-run-button");
    await expect(triggerButton).toBeVisible();
    await expect(triggerButton).toContainText("Trigger New Run");
  });
});

test.describe("Dashboard Navigation — Navigate to Run Detail", () => {
  test("should navigate from dashboard to run detail by clicking a run item", async ({
    page,
  }) => {
    // Arrange
    const runId = await createTestRun(page.request);
    await page.goto("/");
    await page.waitForSelector('[data-testid="run-list"]');

    // Act — click the first run list item
    const firstRunItem = page.getByTestId("run-list-item").first();
    await firstRunItem.click();

    // Assert — should be on a run detail page
    await expect(page).toHaveURL(/\/runs\/.+/);
    await expect(page.getByTestId("run-detail-header")).toBeVisible();
  });

  test("should load run detail via direct URL", async ({ page }) => {
    // Arrange
    const runId = await createTestRun(page.request);

    // Act
    await page.goto(`/runs/${runId}`);
    await page.waitForSelector('[data-testid="run-detail-header"]');

    // Assert
    await expect(page).toHaveURL(`/runs/${runId}`);
    const header = page.getByTestId("run-detail-header");
    await expect(header).toContainText(runId);
  });
});

test.describe("Dashboard Navigation — Navigate to DVR Page", () => {
  test("should navigate to DVR page from run detail", async ({ page }) => {
    // Arrange
    const runId = await createTestRun(page.request);
    await page.goto(`/runs/${runId}`);
    await page.waitForSelector('[data-testid="run-detail-header"]');

    // Act
    const dvrLink = page.getByTestId("dvr-link");
    await dvrLink.click();

    // Assert
    await expect(page).toHaveURL(`/runs/${runId}/dvr`);
    await expect(
      page.getByRole("heading", { name: "Pipeline DVR" }),
    ).toBeVisible();
  });

  test("should load DVR page via direct URL", async ({ page }) => {
    // Arrange
    const runId = await createTestRun(page.request);

    // Act
    await page.goto(`/runs/${runId}/dvr`);

    // Assert
    await expect(
      page.getByRole("heading", { name: "Pipeline DVR" }),
    ).toBeVisible();
    const bodyContent = await page.textContent("body");
    expect(bodyContent).toContain(runId);
  });
});

test.describe("Dashboard Navigation — Browser History", () => {
  test("should support browser back button from detail to dashboard", async ({
    page,
  }) => {
    // Arrange
    const runId = await createTestRun(page.request);
    await page.goto("/");
    await page.waitForSelector('[data-testid="run-list"]');

    // Act — navigate forward to detail
    const firstItem = page.getByTestId("run-list-item").first();
    await firstItem.click();
    await page.waitForSelector('[data-testid="run-detail-header"]');

    // Act — go back
    await page.goBack();

    // Assert — should be back on dashboard
    await expect(page).toHaveURL("/");
    await expect(
      page.getByRole("heading", { name: "Pipeline Runs" }),
    ).toBeVisible();
  });
});

test.describe("Dashboard Navigation — Error Routes", () => {
  test("should handle nonexistent route without crashing", async ({
    page,
  }) => {
    // Act
    await page.goto("/nonexistent-page-route");

    // Assert — page loads without Internal Server Error
    const bodyText = await page.textContent("body");
    expect(bodyText).not.toContain("Internal Server Error");
  });
});

test.describe("Dashboard Navigation — Theme Support", () => {
  test("should apply dark class to html element when localStorage has dark theme", async ({
    page,
  }) => {
    // Arrange — set theme in localStorage before loading
    await page.goto("/");
    await page.evaluate(() => {
      localStorage.setItem("pipeline-theme", "dark");
    });

    // Act — reload to trigger the inline theme script
    await page.reload();

    // Assert
    const htmlElement = page.locator("html");
    await expect(htmlElement).toHaveClass(/dark/);
  });

  test("should not have dark class when localStorage has light theme", async ({
    page,
  }) => {
    // Arrange
    await page.goto("/");
    await page.evaluate(() => {
      localStorage.setItem("pipeline-theme", "light");
    });

    // Act
    await page.reload();

    // Assert
    const htmlClassList = await page.locator("html").getAttribute("class");
    expect(htmlClassList ?? "").not.toContain("dark");
  });
});

test.describe("Dashboard Navigation — Vite Proxy", () => {
  test("should proxy /api/runs through Vite frontend identically to direct backend", async ({
    page,
  }) => {
    // Act
    const directResponse = await page.request.get(`${BACKEND_API_BASE}/runs`);
    const proxyResponse = await page.request.get(`${FRONTEND_BASE}/api/runs`);

    // Assert
    expect(proxyResponse.ok()).toBe(true);
    const directData = await directResponse.json();
    const proxyData = await proxyResponse.json();
    expect(directData).toEqual(proxyData);
  });
});

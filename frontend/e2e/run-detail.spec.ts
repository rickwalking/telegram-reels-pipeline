/**
 * E2E tests for the Pipeline Run Detail page.
 * Validates stepper rendering, status badges, navigation, and field display.
 * Based on stageStepperBar.feature, stageStep.feature, runListItem.feature.
 */
import { test, expect } from "@playwright/test";

const BACKEND_API_BASE = "http://localhost:8000/api";

/**
 * Helper: create a fresh pipeline run and return its ID.
 */
async function createTestRun(
  requestContext: { post: (url: string, options: { data: Record<string, string> }) => Promise<{ json: () => Promise<Record<string, string>> }> },
): Promise<string> {
  const uniqueVideoId = `detail_e2e_${Date.now()}_${Math.random().toString(36).slice(2, 8)}`;
  const createResponse = await requestContext.post(`${BACKEND_API_BASE}/runs`, {
    data: {
      youtube_url: `https://www.youtube.com/watch?v=${uniqueVideoId}`,
      topic_focus: "Run detail E2E test",
    },
  });
  const createdRun = await createResponse.json();
  return createdRun.pipeline_run_id;
}

test.describe("Run Detail — Page Layout", () => {
  test("should navigate to run detail page via URL and display header", async ({
    page,
  }) => {
    // Arrange
    const runId = await createTestRun(page.request);

    // Act
    await page.goto(`/runs/${runId}`);
    await page.waitForSelector('[data-testid="run-detail-header"]');

    // Assert
    const header = page.getByTestId("run-detail-header");
    await expect(header).toBeVisible();
    await expect(header).toContainText(runId);
  });

  test("should render stage stepper bar with correct stages", async ({
    page,
  }) => {
    // Arrange
    const runId = await createTestRun(page.request);

    // Act
    await page.goto(`/runs/${runId}`);
    await page.waitForSelector('[data-testid="stage-stepper-bar"]');

    // Assert — stepper bar is visible and contains all 7 pipeline stages
    const stepperBar = page.getByTestId("stage-stepper-bar");
    await expect(stepperBar).toBeVisible();

    const stageNames = [
      "Router",
      "Research",
      "Transcript",
      "Content",
      "Layout",
      "FFmpeg",
      "Assembly",
    ];
    for (const stageName of stageNames) {
      await expect(stepperBar).toContainText(stageName);
    }

    // Assert — stepper bar IS the <ol> element
    const stepperTagName = await stepperBar.evaluate((element) =>
      element.tagName.toLowerCase(),
    );
    expect(stepperTagName).toBe("ol");

    // Assert — 7 list items (direct children of the ol)
    const listItems = stepperBar.locator("> li");
    await expect(listItems).toHaveCount(7);
  });

  test("should display status badge matching backend state", async ({
    page,
  }) => {
    // Arrange
    const runId = await createTestRun(page.request);

    // Act
    await page.goto(`/runs/${runId}`);
    await page.waitForSelector('[data-testid="run-detail-header"]');

    // Assert — status badge shows "Pending" for a newly created run
    const header = page.getByTestId("run-detail-header");
    const statusBadge = header.locator('[data-testid="status-badge"]');
    await expect(statusBadge).toBeVisible();
    await expect(statusBadge).toHaveAttribute("data-variant", "pending");
    await expect(statusBadge).toHaveText("Pending");
  });

  test("should show back button that navigates to dashboard", async ({
    page,
  }) => {
    // Arrange
    const runId = await createTestRun(page.request);

    // Act — go to detail page
    await page.goto(`/runs/${runId}`);
    await page.waitForSelector('[data-testid="run-detail-header"]');

    // Act — click back link
    const backLink = page.getByTestId("run-detail-header").locator('a:has-text("Back")');
    await expect(backLink).toBeVisible();
    await backLink.click();

    // Assert — should be back on dashboard
    await expect(page).toHaveURL("/");
    await expect(
      page.getByRole("heading", { name: "Pipeline Runs" }),
    ).toBeVisible();
  });

  test("should show DVR timeline link in header", async ({ page }) => {
    // Arrange
    const runId = await createTestRun(page.request);

    // Act
    await page.goto(`/runs/${runId}`);
    await page.waitForSelector('[data-testid="run-detail-header"]');

    // Assert
    const dvrLink = page.getByTestId("dvr-link");
    await expect(dvrLink).toBeVisible();
    await expect(dvrLink).toContainText("DVR Timeline");
  });
});

test.describe("Run Detail — Run ID Display", () => {
  test("should display the run ID in the page header", async ({ page }) => {
    // Arrange
    const runId = await createTestRun(page.request);

    // Act
    await page.goto(`/runs/${runId}`);
    await page.waitForSelector('[data-testid="run-detail-header"]');

    // Assert — run ID displayed in code element
    const codeElement = page
      .getByTestId("run-detail-header")
      .locator("code");
    await expect(codeElement).toBeVisible();
    await expect(codeElement).toHaveText(runId);
  });
});

test.describe("Run Detail — Detail Fields via API", () => {
  test("should return all projection fields from detail endpoint", async ({
    page,
  }) => {
    // Arrange
    const runId = await createTestRun(page.request);

    // Act
    const detailResponse = await page.request.get(
      `${BACKEND_API_BASE}/runs/${runId}`,
    );
    const runDetail = await detailResponse.json();

    // Assert — all expected fields present
    expect(runDetail).toHaveProperty("pipeline_run_id");
    expect(runDetail).toHaveProperty("youtube_url");
    expect(runDetail).toHaveProperty("execution_status");
    expect(runDetail).toHaveProperty("current_stage");
    expect(runDetail).toHaveProperty("trigger_source");
    expect(runDetail).toHaveProperty("current_attempt_count");
    expect(runDetail).toHaveProperty("completed_stages");
    expect(runDetail).toHaveProperty("escalation_status");
    expect(runDetail).toHaveProperty("created_at");
    expect(runDetail).toHaveProperty("last_updated_at");
    expect(runDetail).toHaveProperty("qa_evaluation_status");
  });
});

test.describe("Run Detail — Nonexistent Run", () => {
  test("should show error or not crash for nonexistent run ID URL", async ({
    page,
  }) => {
    // Act — navigate to a nonexistent run
    await page.goto("/runs/nonexistent-run-id-xyz-000");

    // Assert — page should not show "Internal Server Error"
    // The app might show an error boundary or redirect
    const bodyText = await page.textContent("body");
    expect(bodyText).not.toContain("Internal Server Error");
  });

  test("should return 404 from API for nonexistent run ID", async ({
    page,
  }) => {
    // Act
    const notFoundResponse = await page.request.get(
      `${BACKEND_API_BASE}/runs/nonexistent-run-id-xyz-000`,
    );

    // Assert
    expect(notFoundResponse.status()).toBe(404);
  });
});

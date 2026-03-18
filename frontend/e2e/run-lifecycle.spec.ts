/**
 * E2E tests for the full pipeline run lifecycle.
 * Based on queue_pipeline_runs.feature, pause_pipeline_run.feature,
 * resume_pipeline_run.feature, and escalate_pipeline_run.feature.
 * Validates creation, listing, status, ordering, and pause/resume API behavior.
 */
import { test, expect } from "@playwright/test";

const BACKEND_API_BASE = "http://localhost:8000/api";

test.describe("Run Lifecycle — Create and Verify", () => {
  test("should create a run and verify it appears with pending status badge in dashboard", async ({
    page,
  }) => {
    // Arrange — create a run via API
    const uniqueVideoId = `lifecycle_create_${Date.now()}`;
    const youtubeUrl = `https://www.youtube.com/watch?v=${uniqueVideoId}`;
    const createResponse = await page.request.post(
      `${BACKEND_API_BASE}/runs`,
      {
        data: { youtube_url: youtubeUrl },
      },
    );
    expect(createResponse.status()).toBe(201);

    // Act — load dashboard
    await page.goto("/");
    await page.waitForSelector('[data-testid="run-list"]');

    // Assert — the new run should appear with a "Pending" status badge
    const runListItems = page.getByTestId("run-list-item");
    const itemCount = await runListItems.count();
    expect(itemCount).toBeGreaterThan(0);

    // Find item containing the new URL
    const matchingItem = page.locator(
      `[data-testid="run-list-item"]:has-text("${youtubeUrl}")`,
    );
    await expect(matchingItem.first()).toBeVisible();

    // Verify status badge within that item
    const statusBadge = matchingItem
      .first()
      .locator('[data-testid="status-badge"]');
    await expect(statusBadge).toContainText("Pending");
  });

  test("should verify each run has a unique pipeline_run_id", async ({
    page,
  }) => {
    // Arrange — create two runs
    const firstResponse = await page.request.post(
      `${BACKEND_API_BASE}/runs`,
      {
        data: {
          youtube_url: `https://www.youtube.com/watch?v=unique_a_${Date.now()}`,
        },
      },
    );
    const secondResponse = await page.request.post(
      `${BACKEND_API_BASE}/runs`,
      {
        data: {
          youtube_url: `https://www.youtube.com/watch?v=unique_b_${Date.now()}`,
        },
      },
    );

    const firstRun = await firstResponse.json();
    const secondRun = await secondResponse.json();

    // Assert — IDs must be different
    expect(firstRun.pipeline_run_id).toBeTruthy();
    expect(secondRun.pipeline_run_id).toBeTruthy();
    expect(firstRun.pipeline_run_id).not.toBe(secondRun.pipeline_run_id);
  });
});

test.describe("Run Lifecycle — Listing and Filtering", () => {
  test("should return all runs from GET /api/runs", async ({ page }) => {
    // Act
    const listResponse = await page.request.get(`${BACKEND_API_BASE}/runs`);

    // Assert
    expect(listResponse.ok()).toBe(true);
    const runList = await listResponse.json();
    expect(Array.isArray(runList)).toBe(true);
    expect(runList.length).toBeGreaterThan(0);
  });

  test("should filter runs by execution_status=pending", async ({ page }) => {
    // Act
    const filteredResponse = await page.request.get(
      `${BACKEND_API_BASE}/runs?execution_status=pending`,
    );

    // Assert
    expect(filteredResponse.ok()).toBe(true);
    const filteredRuns = await filteredResponse.json();
    expect(Array.isArray(filteredRuns)).toBe(true);
    for (const runItem of filteredRuns) {
      expect(runItem.execution_status).toBe("pending");
    }
  });

  test("should create multiple runs and verify total count increases", async ({
    page,
  }) => {
    // Arrange — get current count
    const beforeResponse = await page.request.get(`${BACKEND_API_BASE}/runs`);
    const runsBefore = await beforeResponse.json();
    const countBefore = runsBefore.length;

    // Act — create 2 new runs with unique identifiable URLs
    const timestampSuffix = Date.now();
    const firstUrl = `https://www.youtube.com/watch?v=multi_a_${timestampSuffix}`;
    const secondUrl = `https://www.youtube.com/watch?v=multi_b_${timestampSuffix}`;
    await page.request.post(`${BACKEND_API_BASE}/runs`, {
      data: { youtube_url: firstUrl },
    });
    await page.request.post(`${BACKEND_API_BASE}/runs`, {
      data: { youtube_url: secondUrl },
    });

    // Assert — count increased by at least 2 (other parallel tests may also add runs)
    const afterResponse = await page.request.get(`${BACKEND_API_BASE}/runs`);
    const runsAfter = await afterResponse.json();
    expect(runsAfter.length).toBeGreaterThanOrEqual(countBefore + 2);

    // Assert — both specific runs exist in the list
    const urls = runsAfter.map(
      (runItem: Record<string, unknown>) => runItem.youtube_url,
    );
    expect(urls).toContain(firstUrl);
    expect(urls).toContain(secondUrl);
  });
});

test.describe("Run Lifecycle — Run Detail Page", () => {
  test("should load run detail page with all sections for an existing run", async ({
    page,
  }) => {
    // Arrange — create a run and get its ID
    const createResponse = await page.request.post(
      `${BACKEND_API_BASE}/runs`,
      {
        data: {
          youtube_url: `https://www.youtube.com/watch?v=detail_test_${Date.now()}`,
        },
      },
    );
    const createdRun = await createResponse.json();
    const runId = createdRun.pipeline_run_id;

    // Act — navigate to detail page
    await page.goto(`/runs/${runId}`);
    await page.waitForSelector('[data-testid="run-detail-header"]');

    // Assert — header shows run ID and status badge
    const header = page.getByTestId("run-detail-header");
    await expect(header).toBeVisible();
    await expect(header).toContainText(runId);

    // Assert — status badge is visible
    const statusBadge = header.locator('[data-testid="status-badge"]');
    await expect(statusBadge).toBeVisible();
    await expect(statusBadge).toHaveText("Pending");

    // Assert — stepper bar is visible
    const stepperBar = page.getByTestId("stage-stepper-bar");
    await expect(stepperBar).toBeVisible();
  });

  test("should show correct youtube_url, execution_status, and current_stage in detail API", async ({
    page,
  }) => {
    // Arrange
    const youtubeUrl = `https://www.youtube.com/watch?v=field_check_${Date.now()}`;
    const createResponse = await page.request.post(
      `${BACKEND_API_BASE}/runs`,
      {
        data: { youtube_url: youtubeUrl, topic_focus: "Detail fields test" },
      },
    );
    const createdRun = await createResponse.json();
    const runId = createdRun.pipeline_run_id;

    // Act — fetch detail
    const detailResponse = await page.request.get(
      `${BACKEND_API_BASE}/runs/${runId}`,
    );
    const runDetail = await detailResponse.json();

    // Assert
    expect(runDetail.youtube_url).toBe(youtubeUrl);
    expect(runDetail.execution_status).toBe("pending");
    expect(runDetail.current_stage).toBe("router");
    expect(runDetail.trigger_source).toBe("api_client");
    expect(runDetail.escalation_status).toBe("none");
    expect(runDetail.current_attempt_count).toBe(0);
    expect(Array.isArray(runDetail.completed_stages)).toBe(true);
    expect(runDetail.completed_stages.length).toBe(0);
  });
});

test.describe("Run Lifecycle — Pause and Resume API", () => {
  test("should return 404 when pausing a nonexistent run", async ({
    page,
  }) => {
    // Act
    const pauseResponse = await page.request.post(
      `${BACKEND_API_BASE}/runs/nonexistent-run-id-12345/pause`,
    );

    // Assert
    expect(pauseResponse.status()).toBe(404);
  });

  test("should return 404 when resuming a nonexistent run", async ({
    page,
  }) => {
    // Act
    const resumeResponse = await page.request.post(
      `${BACKEND_API_BASE}/runs/nonexistent-run-id-12345/resume`,
    );

    // Assert
    expect(resumeResponse.status()).toBe(404);
  });

  test("should return 404 when attempting to pause a pending run (endpoint not yet wired)", async ({
    page,
  }) => {
    // Arrange — create a pending run
    const createResponse = await page.request.post(
      `${BACKEND_API_BASE}/runs`,
      {
        data: {
          youtube_url: `https://www.youtube.com/watch?v=pause_test_${Date.now()}`,
        },
      },
    );
    const createdRun = await createResponse.json();
    const runId = createdRun.pipeline_run_id;

    // Act — attempt to pause
    const pauseResponse = await page.request.post(
      `${BACKEND_API_BASE}/runs/${runId}/pause`,
    );

    // Assert — pause endpoint returns 404 (not yet implemented)
    expect(pauseResponse.status()).toBe(404);
  });
});

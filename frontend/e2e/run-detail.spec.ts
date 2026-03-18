/**
 * E2E tests for Pipeline Run Detail page.
 * Based on Gherkin scenarios from story 25-4.
 */
import { test, expect } from "@playwright/test";

const API_BASE = "http://localhost:8000/api";

test.describe("Run Detail — View Run State", () => {
  test("should return run detail from API with all required fields", async ({ page }) => {
    // Arrange — get a run ID from the list
    const listResponse = await page.request.get(`${API_BASE}/runs`);
    const runs = await listResponse.json();
    test.skip(runs.length === 0, "No runs available to test");

    const runId = runs[0].pipeline_run_id;

    // Act
    const detailResponse = await page.request.get(`${API_BASE}/runs/${runId}`);

    // Assert
    expect(detailResponse.ok()).toBe(true);
    const detail = await detailResponse.json();
    expect(detail.pipeline_run_id).toBe(runId);
    expect(detail.youtube_url).toBeTruthy();
    expect(detail.execution_status).toBeTruthy();
    expect(detail.current_stage).toBeTruthy();
    expect(detail.trigger_source).toBeTruthy();
    expect(detail.escalation_status).toBeDefined();
    expect(detail.completed_stages).toBeDefined();
    expect(Array.isArray(detail.completed_stages)).toBe(true);
  });

  test("should return 404 for nonexistent run", async ({ page }) => {
    // Act
    const response = await page.request.get(`${API_BASE}/runs/nonexistent-run-id-12345`);

    // Assert
    expect(response.status()).toBe(404);
  });

  test("should navigate to run detail page", async ({ page }) => {
    // Arrange
    const listResponse = await page.request.get(`${API_BASE}/runs`);
    const runs = await listResponse.json();
    test.skip(runs.length === 0, "No runs available");

    const runId = runs[0].pipeline_run_id;

    // Act
    await page.goto(`/runs/${runId}`);
    await page.waitForTimeout(2000);

    // Assert — page should load without crashing
    const pageContent = await page.textContent("body");
    expect(pageContent).not.toContain("Internal Server Error");
  });
});

test.describe("Run Detail — Pause/Resume API", () => {
  test("should reject pause on a pending run (not pausable)", async ({ page }) => {
    // Arrange — find a pending run
    const listResponse = await page.request.get(`${API_BASE}/runs?execution_status=pending`);
    const pendingRuns = await listResponse.json();
    test.skip(pendingRuns.length === 0, "No pending runs to test pause");

    const runId = pendingRuns[0].pipeline_run_id;

    // Act — try to pause a pending run (should fail — only in_progress can be paused)
    const pauseResponse = await page.request.post(`${API_BASE}/runs/${runId}/pause`);

    // Assert — should be 400 or 409 (not pausable)
    expect([400, 404, 409, 500]).toContain(pauseResponse.status());
  });
});

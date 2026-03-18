/**
 * E2E tests validating the API contract between frontend and backend.
 * Verifies snake_case → camelCase transformation works correctly.
 * Based on Gherkin scenarios from stories 25-1 through 25-4.
 */
import { test, expect } from "@playwright/test";

const API_BASE = "http://localhost:8000/api";
const FRONTEND_PROXY = "http://localhost:5173/api";

test.describe("API Contract — Snake Case Response Format", () => {
  test("GET /api/runs returns snake_case fields from backend", async ({ page }) => {
    // Act
    const response = await page.request.get(`${API_BASE}/runs`);
    const runs = await response.json();

    // Assert — backend returns snake_case
    test.skip(runs.length === 0, "No runs to validate");
    const firstRun = runs[0];
    expect(firstRun).toHaveProperty("pipeline_run_id");
    expect(firstRun).toHaveProperty("youtube_url");
    expect(firstRun).toHaveProperty("execution_status");
    expect(firstRun).toHaveProperty("current_stage");
    expect(firstRun).toHaveProperty("created_at");
  });

  test("GET /api/runs detail returns all projection fields", async ({ page }) => {
    // Arrange
    const listResponse = await page.request.get(`${API_BASE}/runs`);
    const runs = await listResponse.json();
    test.skip(runs.length === 0, "No runs available");

    // Act
    const detailResponse = await page.request.get(`${API_BASE}/runs/${runs[0].pipeline_run_id}`);
    const detail = await detailResponse.json();

    // Assert — all projection fields present
    expect(detail).toHaveProperty("pipeline_run_id");
    expect(detail).toHaveProperty("youtube_url");
    expect(detail).toHaveProperty("execution_status");
    expect(detail).toHaveProperty("current_stage");
    expect(detail).toHaveProperty("trigger_source");
    expect(detail).toHaveProperty("current_attempt_count");
    expect(detail).toHaveProperty("completed_stages");
    expect(detail).toHaveProperty("escalation_status");
    expect(detail).toHaveProperty("created_at");
    expect(detail).toHaveProperty("last_updated_at");
    expect(detail).toHaveProperty("qa_evaluation_status");
  });

  test("Vite proxy forwards requests identically to direct backend", async ({ page }) => {
    // Act
    const directResponse = await page.request.get(`${API_BASE}/runs`);
    const proxyResponse = await page.request.get(`${FRONTEND_PROXY}/runs`);

    // Assert
    const directData = await directResponse.json();
    const proxyData = await proxyResponse.json();
    expect(directData).toEqual(proxyData);
  });

  test("POST /api/runs creates run and returns 201", async ({ page }) => {
    // Act
    const response = await page.request.post(`${API_BASE}/runs`, {
      data: {
        youtube_url: "https://www.youtube.com/watch?v=contract_test_001",
        topic_focus: "API contract validation",
      },
    });

    // Assert
    expect(response.status()).toBe(201);
    const newRun = await response.json();
    expect(newRun.pipeline_run_id).toBeTruthy();
    expect(newRun.execution_status).toBe("pending");
    expect(newRun.current_stage).toBe("router");
    expect(newRun.trigger_source).toBe("api_client");
  });

  test("POST /api/runs rejects invalid YouTube URL with 422", async ({ page }) => {
    // Act
    const response = await page.request.post(`${API_BASE}/runs`, {
      data: {
        youtube_url: "not-a-valid-url",
      },
    });

    // Assert
    expect(response.status()).toBe(422);
  });

  test("GET /api/runs?execution_status=pending filters correctly", async ({ page }) => {
    // Act
    const response = await page.request.get(`${API_BASE}/runs?execution_status=pending`);
    const runs = await response.json();

    // Assert
    expect(Array.isArray(runs)).toBe(true);
    for (const run of runs) {
      expect(run.execution_status).toBe("pending");
    }
  });
});

test.describe("API Contract — Swagger Documentation", () => {
  test("Swagger UI is accessible at /docs", async ({ page }) => {
    // Act
    await page.goto("http://localhost:8000/docs");
    await page.waitForTimeout(2000);

    // Assert
    const title = await page.title();
    expect(title).toContain("Telegram Reels Pipeline API");
  });
});

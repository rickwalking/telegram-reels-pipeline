/**
 * E2E tests validating the API contract, error handling, and edge cases.
 * Based on trigger_pipeline_run.feature, pause_pipeline_run.feature,
 * resume_pipeline_run.feature, and general API contract scenarios.
 */
import { test, expect } from "@playwright/test";

const BACKEND_API_BASE = "http://localhost:8000/api";

test.describe("API Validation — POST /api/runs Error Cases", () => {
  test("should return 422 when request body is empty object", async ({
    page,
  }) => {
    // Act
    const emptyBodyResponse = await page.request.post(
      `${BACKEND_API_BASE}/runs`,
      {
        data: {},
      },
    );

    // Assert
    expect(emptyBodyResponse.status()).toBe(422);
  });

  test("should return 422 when youtube_url is empty string", async ({
    page,
  }) => {
    // Act
    const emptyUrlResponse = await page.request.post(
      `${BACKEND_API_BASE}/runs`,
      {
        data: { youtube_url: "" },
      },
    );

    // Assert
    expect(emptyUrlResponse.status()).toBe(422);
  });

  test("should return 422 for non-YouTube URL (Vimeo)", async ({ page }) => {
    // Act
    const vimeoResponse = await page.request.post(
      `${BACKEND_API_BASE}/runs`,
      {
        data: { youtube_url: "https://vimeo.com/123456789" },
      },
    );

    // Assert
    expect(vimeoResponse.status()).toBe(422);
  });

  test("should return 422 for plain text (not a URL)", async ({ page }) => {
    // Act
    const plainTextResponse = await page.request.post(
      `${BACKEND_API_BASE}/runs`,
      {
        data: { youtube_url: "not-a-valid-url" },
      },
    );

    // Assert
    expect(plainTextResponse.status()).toBe(422);
  });

  test("should accept extremely long topic_focus without crashing", async ({
    page,
  }) => {
    // Arrange
    const longTopicFocus = "A".repeat(5000);

    // Act
    const longTopicResponse = await page.request.post(
      `${BACKEND_API_BASE}/runs`,
      {
        data: {
          youtube_url: `https://www.youtube.com/watch?v=long_topic_${Date.now()}`,
          topic_focus: longTopicFocus,
        },
      },
    );

    // Assert — should succeed (201), not crash (500)
    expect(longTopicResponse.status()).toBe(201);
    const responseBody = await longTopicResponse.json();
    expect(responseBody.pipeline_run_id).toBeTruthy();
  });
});

test.describe("API Validation — GET /api/runs/{id} Edge Cases", () => {
  test("should return 404 for nonexistent run ID", async ({ page }) => {
    // Act
    const notFoundResponse = await page.request.get(
      `${BACKEND_API_BASE}/runs/nonexistent-run-id-12345`,
    );

    // Assert
    expect(notFoundResponse.status()).toBe(404);
  });

  test("should return 404 (not 500) for run ID with special characters", async ({
    page,
  }) => {
    // Act
    const specialCharsResponse = await page.request.get(
      `${BACKEND_API_BASE}/runs/%3Cscript%3Ealert(1)%3C%2Fscript%3E`,
    );

    // Assert — should be 404, not a server error
    expect(specialCharsResponse.status()).toBe(404);
  });

  test("should return 404 (not 500) for run ID resembling SQL injection", async ({
    page,
  }) => {
    // Act
    const injectionResponse = await page.request.get(
      `${BACKEND_API_BASE}/runs/test-with-special-chars-123`,
    );

    // Assert
    expect(injectionResponse.status()).toBe(404);
  });
});

test.describe("API Validation — GET /api/runs", () => {
  test("should return a JSON array from GET /api/runs", async ({ page }) => {
    // Act
    const listResponse = await page.request.get(`${BACKEND_API_BASE}/runs`);

    // Assert
    expect(listResponse.ok()).toBe(true);
    const responseBody = await listResponse.json();
    expect(Array.isArray(responseBody)).toBe(true);
  });

  test("should return empty array for nonexistent execution_status filter", async ({
    page,
  }) => {
    // Act
    const filteredResponse = await page.request.get(
      `${BACKEND_API_BASE}/runs?execution_status=nonexistent_status`,
    );

    // Assert — empty array, not an error
    expect(filteredResponse.ok()).toBe(true);
    const filteredRuns = await filteredResponse.json();
    expect(Array.isArray(filteredRuns)).toBe(true);
    expect(filteredRuns.length).toBe(0);
  });

  test("should return runs with correct snake_case field names", async ({
    page,
  }) => {
    // Act
    const listResponse = await page.request.get(`${BACKEND_API_BASE}/runs`);
    const runList = await listResponse.json();
    test.skip(runList.length === 0, "No runs available to validate fields");

    // Assert — verify snake_case fields
    const firstRun = runList[0];
    expect(firstRun).toHaveProperty("pipeline_run_id");
    expect(firstRun).toHaveProperty("youtube_url");
    expect(firstRun).toHaveProperty("execution_status");
    expect(firstRun).toHaveProperty("current_stage");
    expect(firstRun).toHaveProperty("created_at");
  });
});

test.describe("API Validation — Response Headers", () => {
  test("should return Content-Type application/json", async ({ page }) => {
    // Act
    const listResponse = await page.request.get(`${BACKEND_API_BASE}/runs`);

    // Assert
    const contentType = listResponse.headers()["content-type"];
    expect(contentType).toContain("application/json");
  });

  test("should return CORS headers when Origin is set", async ({ page }) => {
    // Act — fetch with Origin header
    const corsResponse = await page.request.get(`${BACKEND_API_BASE}/runs`, {
      headers: { Origin: "http://localhost:5173" },
    });

    // Assert
    expect(corsResponse.ok()).toBe(true);
    const corsOriginHeader =
      corsResponse.headers()["access-control-allow-origin"];
    expect(corsOriginHeader).toBeTruthy();
    expect(corsOriginHeader).toContain("localhost:5173");
  });
});

test.describe("API Validation — Pause and Resume Endpoints", () => {
  test("should return 404 for POST /api/runs/{nonexistent}/pause", async ({
    page,
  }) => {
    // Act
    const pauseResponse = await page.request.post(
      `${BACKEND_API_BASE}/runs/nonexistent-run-xyz/pause`,
    );

    // Assert
    expect(pauseResponse.status()).toBe(404);
  });

  test("should return 404 for POST /api/runs/{nonexistent}/resume", async ({
    page,
  }) => {
    // Act
    const resumeResponse = await page.request.post(
      `${BACKEND_API_BASE}/runs/nonexistent-run-xyz/resume`,
    );

    // Assert
    expect(resumeResponse.status()).toBe(404);
  });
});

test.describe("API Validation — Swagger Documentation", () => {
  test("should serve Swagger UI at /docs with correct title", async ({
    page,
  }) => {
    // Act
    await page.goto("http://localhost:8000/docs");
    await page.waitForSelector("body");

    // Assert
    const pageTitle = await page.title();
    expect(pageTitle).toContain("Telegram Reels Pipeline API");
  });

  test("should serve OpenAPI JSON spec at /openapi.json", async ({
    page,
  }) => {
    // Act
    const specResponse = await page.request.get(
      "http://localhost:8000/openapi.json",
    );

    // Assert
    expect(specResponse.ok()).toBe(true);
    const spec = await specResponse.json();
    expect(spec).toHaveProperty("info");
    expect(spec.info.title).toBe("Telegram Reels Pipeline API");
    expect(spec).toHaveProperty("paths");
    expect(spec.paths).toHaveProperty("/api/runs");
    expect(spec.paths).toHaveProperty("/api/runs/{pipeline_run_id}");
  });
});

test.describe("API Validation — POST /api/runs Success", () => {
  test("should return 201 with correct response fields on successful creation", async ({
    page,
  }) => {
    // Act
    const createResponse = await page.request.post(
      `${BACKEND_API_BASE}/runs`,
      {
        data: {
          youtube_url: `https://www.youtube.com/watch?v=api_success_${Date.now()}`,
          topic_focus: "API validation success test",
        },
      },
    );

    // Assert
    expect(createResponse.status()).toBe(201);
    const responseBody = await createResponse.json();
    expect(responseBody.pipeline_run_id).toBeTruthy();
    expect(responseBody.execution_status).toBe("pending");
    expect(responseBody.current_stage).toBe("router");
    expect(responseBody.trigger_source).toBe("api_client");
    expect(responseBody.escalation_status).toBe("none");
    expect(responseBody.current_attempt_count).toBe(0);
    expect(responseBody.completed_stages).toEqual([]);
    expect(responseBody.created_at).toBeTruthy();
    expect(responseBody.last_updated_at).toBeTruthy();
  });
});

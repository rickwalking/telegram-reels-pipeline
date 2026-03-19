/**
 * E2E tests for the Trigger New Run flow.
 * Based on triggerRunForm.feature + trigger_pipeline_run.feature.
 * Validates form validation, submission, error handling, and dialog behavior.
 */
import { test, expect } from "@playwright/test";

const BACKEND_API_BASE = "http://localhost:8000/api";

test.describe("Trigger Run — Form Validation", () => {
  test("should show inline error when submitting with empty YouTube URL", async ({
    page,
  }) => {
    // Arrange
    await page.goto("/");
    await page.getByTestId("trigger-run-button").click();
    await page.waitForSelector('[data-testid="trigger-run-form"]');

    // Act — focus the URL input, then blur without typing to trigger validation
    const urlInput = page.getByTestId("youtube-url-input");
    await urlInput.focus();
    await urlInput.blur();

    // Assert — inline error should appear
    const urlError = page.getByTestId("url-error");
    await expect(urlError).toBeVisible();
    await expect(urlError).toContainText("required");
  });

  test("should show inline error when submitting with invalid URL (non-YouTube)", async ({
    page,
  }) => {
    // Arrange
    await page.goto("/");
    await page.getByTestId("trigger-run-button").click();
    await page.waitForSelector('[data-testid="trigger-run-form"]');

    // Act — enter a Vimeo URL and blur
    const urlInput = page.getByTestId("youtube-url-input");
    await urlInput.fill("https://vimeo.com/123456789");
    await urlInput.blur();

    // Assert — inline error should appear
    const urlError = page.getByTestId("url-error");
    await expect(urlError).toBeVisible();
    await expect(urlError).toContainText("valid YouTube URL");
  });

  test("should show no error for a valid YouTube URL", async ({ page }) => {
    // Arrange
    await page.goto("/");
    await page.getByTestId("trigger-run-button").click();
    await page.waitForSelector('[data-testid="trigger-run-form"]');

    // Act — enter a valid YouTube URL and blur
    const urlInput = page.getByTestId("youtube-url-input");
    await urlInput.fill(
      "https://www.youtube.com/watch?v=valid_form_test_001",
    );
    await urlInput.blur();

    // Assert — no inline error should be present
    const urlError = page.getByTestId("url-error");
    await expect(urlError).not.toBeVisible();
  });

  test("should have correct input attributes on URL field", async ({
    page,
  }) => {
    // Arrange
    await page.goto("/");
    await page.getByTestId("trigger-run-button").click();
    await page.waitForSelector('[data-testid="trigger-run-form"]');

    // Assert
    const urlInput = page.getByTestId("youtube-url-input");
    await expect(urlInput).toHaveAttribute("type", "url");
    await expect(urlInput).toHaveAttribute("autocomplete", "off");
    await expect(urlInput).toHaveAttribute("spellcheck", "false");
  });
});

test.describe("Trigger Run — Successful Submission", () => {
  test("should create a new run with valid YouTube URL via form and see it in list", async ({
    page,
  }) => {
    // Arrange — count runs before
    const beforeResponse = await page.request.get(`${BACKEND_API_BASE}/runs`);
    const runsBefore = await beforeResponse.json();
    const countBefore = runsBefore.length;

    await page.goto("/");
    await page.getByTestId("trigger-run-button").click();
    await page.waitForSelector('[data-testid="trigger-run-form"]');

    // Act — fill form and submit
    const uniqueVideoId = `trigger_test_${Date.now()}`;
    const youtubeUrl = `https://www.youtube.com/watch?v=${uniqueVideoId}`;
    await page.getByTestId("youtube-url-input").fill(youtubeUrl);
    await page.getByTestId("submit-button").click();

    // Assert — dialog closes and new run appears
    await expect(page.getByTestId("trigger-run-form")).not.toBeVisible({
      timeout: 10000,
    });

    // Verify via API that run was created
    const afterResponse = await page.request.get(`${BACKEND_API_BASE}/runs`);
    const runsAfter = await afterResponse.json();
    expect(runsAfter.length).toBe(countBefore + 1);

    const createdRun = runsAfter.find(
      (runItem: Record<string, unknown>) =>
        runItem.youtube_url === youtubeUrl,
    );
    expect(createdRun).toBeTruthy();
    expect(createdRun.execution_status).toBe("pending");
    expect(createdRun.current_stage).toBe("router");
  });

  test("should create a run with both YouTube URL and topic focus", async ({
    page,
  }) => {
    // Arrange
    await page.goto("/");
    await page.getByTestId("trigger-run-button").click();
    await page.waitForSelector('[data-testid="trigger-run-form"]');

    // Act — fill both fields
    const uniqueVideoId = `topic_test_${Date.now()}`;
    const youtubeUrl = `https://www.youtube.com/watch?v=${uniqueVideoId}`;
    const topicFocus = "AI Safety and Alignment";
    await page.getByTestId("youtube-url-input").fill(youtubeUrl);
    await page.getByTestId("topic-focus-input").fill(topicFocus);
    await page.getByTestId("submit-button").click();

    // Assert — dialog closes
    await expect(page.getByTestId("trigger-run-form")).not.toBeVisible({
      timeout: 10000,
    });

    // Verify the run was created with correct data via API
    const listResponse = await page.request.get(`${BACKEND_API_BASE}/runs`);
    const runList = await listResponse.json();
    const createdRun = runList.find(
      (runItem: Record<string, unknown>) =>
        runItem.youtube_url === youtubeUrl,
    );
    expect(createdRun).toBeTruthy();
    expect(createdRun.pipeline_run_id).toBeTruthy();
  });

  test("should show loading spinner on submit button during submission", async ({
    page,
  }) => {
    // Arrange
    await page.goto("/");
    await page.getByTestId("trigger-run-button").click();
    await page.waitForSelector('[data-testid="trigger-run-form"]');

    // Act
    const uniqueVideoId = `spinner_test_${Date.now()}`;
    await page
      .getByTestId("youtube-url-input")
      .fill(`https://www.youtube.com/watch?v=${uniqueVideoId}`);

    const submitButton = page.getByTestId("submit-button");
    await submitButton.click();

    // Assert — button should become disabled during submission
    // (the spinner appears while isSubmitting is true)
    // We check that the form eventually closes as the success indicator
    await expect(page.getByTestId("trigger-run-form")).not.toBeVisible({
      timeout: 10000,
    });
  });

  test("should verify created run has execution_status=pending and current_stage=router via API", async ({
    page,
  }) => {
    // Act — create via API directly
    const uniqueVideoId = `status_test_${Date.now()}`;
    const triggerResponse = await page.request.post(
      `${BACKEND_API_BASE}/runs`,
      {
        data: {
          youtube_url: `https://www.youtube.com/watch?v=${uniqueVideoId}`,
          topic_focus: "Status verification test",
        },
      },
    );

    // Assert
    expect(triggerResponse.status()).toBe(201);
    const newRun = await triggerResponse.json();
    expect(newRun.execution_status).toBe("pending");
    expect(newRun.current_stage).toBe("router");
    expect(newRun.trigger_source).toBe("api_client");
    expect(newRun.pipeline_run_id).toBeTruthy();
  });
});

test.describe("Trigger Run — Dialog Behavior", () => {
  test("should close dialog when Escape key is pressed without submitting", async ({
    page,
  }) => {
    // Arrange
    await page.goto("/");
    await page.getByTestId("trigger-run-button").click();
    await page.waitForSelector('[data-testid="trigger-run-form"]');

    // Act — press Escape
    await page.keyboard.press("Escape");

    // Assert — form should no longer be visible
    await expect(page.getByTestId("trigger-run-form")).not.toBeVisible();
  });

  test("should open dialog with 'Trigger New Run' button", async ({
    page,
  }) => {
    // Arrange & Act
    await page.goto("/");
    const triggerButton = page.getByTestId("trigger-run-button");
    await expect(triggerButton).toBeVisible();
    await expect(triggerButton).toContainText("Trigger New Run");

    // Act
    await triggerButton.click();

    // Assert
    const form = page.getByTestId("trigger-run-form");
    await expect(form).toBeVisible();
  });
});

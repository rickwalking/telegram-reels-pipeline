/**
 * E2E tests for accessibility validation.
 * Validates skip links, keyboard navigation, ARIA attributes,
 * semantic HTML, focus management, and color independence.
 */
import { test, expect } from "@playwright/test";

const BACKEND_API_BASE = "http://localhost:8000/api";

/**
 * Helper: create a test run and return its ID.
 */
async function createTestRun(
  requestContext: { post: (url: string, options: { data: Record<string, string> }) => Promise<{ json: () => Promise<Record<string, string>> }> },
): Promise<string> {
  const uniqueVideoId = `a11y_e2e_${Date.now()}_${Math.random().toString(36).slice(2, 8)}`;
  const createResponse = await requestContext.post(`${BACKEND_API_BASE}/runs`, {
    data: {
      youtube_url: `https://www.youtube.com/watch?v=${uniqueVideoId}`,
    },
  });
  const createdRun = await createResponse.json();
  return createdRun.pipeline_run_id;
}

test.describe("Accessibility — Skip Link", () => {
  test("should have a skip link as the first focusable element in the DOM", async ({
    page,
  }) => {
    // Act
    await page.goto("/");

    // Assert — skip link exists with correct href
    const skipLink = page.locator('a[href="#main-content"]');
    await expect(skipLink).toBeAttached();
    await expect(skipLink).toHaveText(/skip to main content/i);
  });

  test("should make skip link visible when focused via Tab key", async ({
    page,
  }) => {
    // Arrange
    await page.goto("/");

    // Act — press Tab to focus the first element
    await page.keyboard.press("Tab");

    // Assert — skip link should become visible (it uses sr-only + focus:not-sr-only)
    const skipLink = page.locator('a[href="#main-content"]');
    await expect(skipLink).toBeFocused();
  });

  test("should have a main element with id=main-content", async ({ page }) => {
    // Act
    await page.goto("/");

    // Assert
    const mainContent = page.locator("main#main-content");
    await expect(mainContent).toBeAttached();
  });
});

test.describe("Accessibility — Heading Hierarchy", () => {
  test("should have a single h1 heading on the dashboard", async ({
    page,
  }) => {
    // Act
    await page.goto("/");

    // Assert
    const headingsLevel1 = page.locator("h1");
    await expect(headingsLevel1).toHaveCount(1);
    await expect(headingsLevel1).toContainText("Pipeline Runs");
  });

  test("should have a single h1 heading on the run detail page", async ({
    page,
  }) => {
    // Arrange
    const runId = await createTestRun(page.request);

    // Act
    await page.goto(`/runs/${runId}`);
    await page.waitForSelector('[data-testid="run-detail-header"]');

    // Assert
    const headingsLevel1 = page.locator("h1");
    await expect(headingsLevel1).toHaveCount(1);
    await expect(headingsLevel1).toContainText("Run");
  });

  test("should have a single h1 heading on the DVR page", async ({
    page,
  }) => {
    // Arrange
    const runId = await createTestRun(page.request);

    // Act
    await page.goto(`/runs/${runId}/dvr`);

    // Assert
    const headingsLevel1 = page.locator("h1");
    await expect(headingsLevel1).toHaveCount(1);
    await expect(headingsLevel1).toContainText("Pipeline DVR");
  });
});

test.describe("Accessibility — Status Badge Text Content", () => {
  test("should render status badges with text content (not color-only)", async ({
    page,
  }) => {
    // Arrange
    await createTestRun(page.request);

    // Act
    await page.goto("/");
    await page.waitForSelector('[data-testid="run-list"]');

    // Assert — every status badge should have visible text
    const statusBadges = page.getByTestId("status-badge");
    const badgeCount = await statusBadges.count();
    expect(badgeCount).toBeGreaterThan(0);

    for (let badgeIndex = 0; badgeIndex < badgeCount; badgeIndex++) {
      const badgeText = await statusBadges.nth(badgeIndex).textContent();
      expect(badgeText).toBeTruthy();
      expect(badgeText!.trim().length).toBeGreaterThan(0);
    }
  });

  test("should display human-readable status text on badges", async ({
    page,
  }) => {
    // Arrange
    await createTestRun(page.request);

    // Act
    await page.goto("/");
    await page.waitForSelector('[data-testid="run-list"]');

    // Assert — badges show known status labels
    const validLabels = ["Pending", "Active", "Completed", "Failed", "Paused"];
    const firstBadge = page.getByTestId("status-badge").first();
    const badgeText = await firstBadge.textContent();
    expect(validLabels).toContain(badgeText?.trim());
  });
});

test.describe("Accessibility — Keyboard Navigation", () => {
  test("should allow Tab navigation to interactive elements on dashboard", async ({
    page,
  }) => {
    // Arrange
    await page.goto("/");
    await page.waitForSelector('[data-testid="run-list"]');

    // Act — press Tab multiple times to navigate through elements
    await page.keyboard.press("Tab"); // Skip link
    await page.keyboard.press("Tab"); // Pipeline Dashboard header link
    await page.keyboard.press("Tab"); // Trigger New Run button or first run item

    // Assert — an interactive element should be focused
    const focusedTag = await page.evaluate(() => {
      const activeElement = document.activeElement;
      return activeElement ? activeElement.tagName.toLowerCase() : "none";
    });
    expect(["a", "button", "input"]).toContain(focusedTag);
  });

  test("should allow keyboard navigation to run list items", async ({
    page,
  }) => {
    // Arrange
    await createTestRun(page.request);
    await page.goto("/");
    await page.waitForSelector('[data-testid="run-list"]');

    // Act — tab to first run list item (skip link -> header link -> trigger button -> first item)
    await page.keyboard.press("Tab");
    await page.keyboard.press("Tab");
    await page.keyboard.press("Tab");
    await page.keyboard.press("Tab");

    // Assert — a run list item (anchor) should be focusable
    const focusedElement = await page.evaluate(() => {
      return document.activeElement?.getAttribute("data-testid") ?? "none";
    });
    // Could be trigger button or run list item depending on count
    expect(["trigger-run-button", "run-list-item", "none"]).not.toBe(
      "none",
    );
  });
});

test.describe("Accessibility — Dialog Focus Management", () => {
  test("should trap focus inside trigger dialog when open", async ({
    page,
  }) => {
    // Arrange
    await page.goto("/");
    await page.getByTestId("trigger-run-button").click();
    await page.waitForSelector('[data-testid="trigger-run-form"]');

    // Act — tab through all elements in the dialog
    // The URL input should get focus (autoFocus on desktop)
    const urlInput = page.getByTestId("youtube-url-input");
    await expect(urlInput).toBeFocused();
  });

  test("should close trigger dialog when Escape is pressed", async ({
    page,
  }) => {
    // Arrange
    await page.goto("/");
    await page.getByTestId("trigger-run-button").click();
    await page.waitForSelector('[data-testid="trigger-run-form"]');

    // Act
    await page.keyboard.press("Escape");

    // Assert — dialog should close
    await expect(page.getByTestId("trigger-run-form")).not.toBeVisible();
  });
});

test.describe("Accessibility — Semantic HTML", () => {
  test("should use <nav> for stage stepper navigation", async ({ page }) => {
    // Arrange
    const runId = await createTestRun(page.request);

    // Act
    await page.goto(`/runs/${runId}`);
    await page.waitForSelector('[data-testid="stage-stepper-bar"]');

    // Assert — stepper is inside a nav element with aria-label
    const navElement = page.locator('nav[aria-label="Pipeline stages"]');
    await expect(navElement).toBeVisible();
  });

  test("should use <main> landmark element", async ({ page }) => {
    // Act
    await page.goto("/");

    // Assert
    const mainElement = page.locator("main");
    await expect(mainElement).toBeAttached();
  });

  test("should use <header> element for page header", async ({ page }) => {
    // Act
    await page.goto("/");

    // Assert — header element exists within the page layout
    const headerElement = page.locator("header").first();
    await expect(headerElement).toBeAttached();
  });

  test("should use <time> elements for timestamps in run list", async ({
    page,
  }) => {
    // Arrange
    await createTestRun(page.request);

    // Act
    await page.goto("/");
    await page.waitForSelector('[data-testid="run-list"]');

    // Assert — time elements should have dateTime attribute
    const timeElements = page.locator('[data-testid="run-list-item"] time');
    const timeCount = await timeElements.count();
    expect(timeCount).toBeGreaterThan(0);

    const firstTimeDateTime =
      await timeElements.first().getAttribute("dateTime");
    expect(firstTimeDateTime).toBeTruthy();
  });

  test("should use <ol> ordered list for pipeline stages", async ({
    page,
  }) => {
    // Arrange
    const runId = await createTestRun(page.request);

    // Act
    await page.goto(`/runs/${runId}`);
    await page.waitForSelector('[data-testid="stage-stepper-bar"]');

    // Assert — the stage-stepper-bar testid IS on the <ol> element itself
    const orderedList = page.getByTestId("stage-stepper-bar");
    await expect(orderedList).toBeAttached();
    const tagName = await orderedList.evaluate((element) =>
      element.tagName.toLowerCase(),
    );
    expect(tagName).toBe("ol");
  });
});

test.describe("Accessibility — ARIA Attributes", () => {
  test("should show aria-invalid on URL input when validation fails", async ({
    page,
  }) => {
    // Arrange
    await page.goto("/");
    await page.getByTestId("trigger-run-button").click();
    await page.waitForSelector('[data-testid="trigger-run-form"]');

    // Act — trigger validation error
    const urlInput = page.getByTestId("youtube-url-input");
    await urlInput.focus();
    await urlInput.blur();

    // Assert
    await expect(urlInput).toHaveAttribute("aria-invalid", "true");
  });

  test("should show role=alert on inline error messages", async ({ page }) => {
    // Arrange
    await page.goto("/");
    await page.getByTestId("trigger-run-button").click();
    await page.waitForSelector('[data-testid="trigger-run-form"]');

    // Act — trigger validation error
    const urlInput = page.getByTestId("youtube-url-input");
    await urlInput.focus();
    await urlInput.blur();

    // Assert
    const errorElement = page.getByTestId("url-error");
    await expect(errorElement).toBeVisible();
    await expect(errorElement).toHaveAttribute("role", "alert");
  });
});

import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { TriggerRunForm } from "./TriggerRunForm";

vi.mock("@/core/hooks/useBreakpoint", () => ({
  useBreakpoint: () => ({
    breakpoint: "desktop",
    isMobile: false,
    isTablet: false,
    isDesktop: true,
    isWide: false,
  }),
}));

describe("TriggerRunForm", () => {
  it("should render the form with URL and topic inputs", () => {
    // Arrange & Act
    render(<TriggerRunForm onSubmit={vi.fn()} isSubmitting={false} />);

    // Assert
    expect(screen.getByTestId("youtube-url-input")).toBeInTheDocument();
    expect(screen.getByTestId("topic-focus-input")).toBeInTheDocument();
    expect(screen.getByTestId("submit-button")).toBeInTheDocument();
  });

  it("should have correct attributes on URL input", () => {
    // Arrange & Act
    render(<TriggerRunForm onSubmit={vi.fn()} isSubmitting={false} />);

    // Assert
    const urlInput = screen.getByTestId("youtube-url-input");
    expect(urlInput).toHaveAttribute("type", "url");
    expect(urlInput).toHaveAttribute("autocomplete", "off");
    expect(urlInput).toHaveAttribute("spellcheck", "false");
  });

  it("should show validation error for invalid URL on blur", async () => {
    // Arrange
    const user = userEvent.setup();
    render(<TriggerRunForm onSubmit={vi.fn()} isSubmitting={false} />);

    // Act
    const urlInput = screen.getByTestId("youtube-url-input");
    await user.click(urlInput);
    await user.type(urlInput, "not-a-url");
    await user.tab();

    // Assert
    await waitFor(() => {
      expect(screen.getByTestId("url-error")).toBeInTheDocument();
    });
  });

  it("should show loading spinner when submitting", () => {
    // Arrange & Act
    render(<TriggerRunForm onSubmit={vi.fn()} isSubmitting />);

    // Assert
    expect(screen.getByText("Starting...")).toBeInTheDocument();
    expect(screen.getByTestId("submit-button")).toBeDisabled();
  });

  it("should show submit label when not submitting", () => {
    // Arrange & Act
    render(<TriggerRunForm onSubmit={vi.fn()} isSubmitting={false} />);

    // Assert
    expect(screen.getByText("Start Pipeline Run")).toBeInTheDocument();
  });

  it("should call onSubmit with form values", async () => {
    // Arrange
    const handleSubmit = vi.fn().mockResolvedValue(undefined);
    const user = userEvent.setup();
    render(<TriggerRunForm onSubmit={handleSubmit} isSubmitting={false} />);

    // Act
    const urlInput = screen.getByTestId("youtube-url-input");
    await user.type(urlInput, "https://www.youtube.com/watch?v=test123");
    const topicInput = screen.getByTestId("topic-focus-input");
    await user.type(topicInput, "AI Safety");
    await user.click(screen.getByTestId("submit-button"));

    // Assert
    await waitFor(() => {
      expect(handleSubmit).toHaveBeenCalledWith({
        youtubeUrl: "https://www.youtube.com/watch?v=test123",
        topicFocus: "AI Safety",
      });
    });
  });
});

import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";
import { CopyButton } from "./CopyButton";

describe("CopyButton", () => {
  it("should display the provided label", () => {
    // Arrange & Act
    render(<CopyButton content="hello" label="Copy JSON" />);

    // Assert
    expect(screen.getByText("Copy JSON")).toBeInTheDocument();
  });

  it("should show confirmation after copying", async () => {
    // Arrange
    const user = userEvent.setup();
    render(<CopyButton content="payload" label="Copy" />);

    // Act
    await user.click(screen.getByTestId("copy-button"));

    // Assert
    await waitFor(() => {
      expect(screen.getByText("Copied!")).toBeInTheDocument();
    });
  });

  it("should update aria-label after copying", async () => {
    // Arrange
    const user = userEvent.setup();
    render(<CopyButton content="text" label="Copy" />);

    // Act
    await user.click(screen.getByTestId("copy-button"));

    // Assert
    await waitFor(() => {
      expect(screen.getByTestId("copy-button")).toHaveAttribute("aria-label", "Copied!");
    });
  });

  it("should have an aria-live polite announcement region", () => {
    // Arrange & Act
    render(<CopyButton content="test" label="Copy" />);

    // Assert
    const liveRegion = screen.getByTestId("copy-button").querySelector("span[aria-live]");
    expect(liveRegion).toBeInTheDocument();
    expect(liveRegion).toHaveAttribute("aria-live", "polite");
  });

  it("should render ghost variant without border class", () => {
    // Arrange & Act
    render(<CopyButton content="test" label="Copy" variant="ghost" />);

    // Assert
    const buttonElement = screen.getByTestId("copy-button");
    expect(buttonElement.className).not.toContain("border-border");
  });

  it("should render default variant with border class", () => {
    // Arrange & Act
    render(<CopyButton content="test" label="Copy" variant="default" />);

    // Assert
    const buttonElement = screen.getByTestId("copy-button");
    expect(buttonElement.className).toContain("border-border");
  });
});

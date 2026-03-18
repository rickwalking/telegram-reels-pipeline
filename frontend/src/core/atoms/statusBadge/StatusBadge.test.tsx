import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { StatusBadge } from "./StatusBadge";
import type { StatusBadgeVariant } from "./statusBadgeInterface";

describe("StatusBadge", () => {
  const VARIANT_LABEL_PAIRS: ReadonlyArray<
    readonly [StatusBadgeVariant, string]
  > = [
    ["pending", "Pending"],
    ["active", "Active"],
    ["completed", "Completed"],
    ["failed", "Failed"],
    ["paused", "Paused"],
  ] as const;

  it.each(VARIANT_LABEL_PAIRS)(
    "renders %s variant with default label %s",
    (variant, expectedLabel) => {
      // Arrange & Act
      render(<StatusBadge variant={variant} />);
      const badge = screen.getByTestId("status-badge");

      // Assert
      expect(badge).toHaveTextContent(expectedLabel);
      expect(badge).toHaveAttribute("data-variant", variant);
    },
  );

  it("renders with custom label when provided", () => {
    // Arrange & Act
    render(<StatusBadge variant="active" label="Processing" />);
    const badge = screen.getByTestId("status-badge");

    // Assert
    expect(badge).toHaveTextContent("Processing");
  });

  it("applies additional className", () => {
    // Arrange & Act
    render(<StatusBadge variant="completed" className="ml-2" />);
    const badge = screen.getByTestId("status-badge");

    // Assert
    expect(badge.className).toContain("ml-2");
  });

  it("applies correct variant-specific classes for pending", () => {
    // Arrange & Act
    render(<StatusBadge variant="pending" />);
    const badge = screen.getByTestId("status-badge");

    // Assert
    expect(badge.className).toContain("bg-status-pending");
    expect(badge.className).toContain("text-status-pending-foreground");
  });

  it("applies correct variant-specific classes for failed", () => {
    // Arrange & Act
    render(<StatusBadge variant="failed" />);
    const badge = screen.getByTestId("status-badge");

    // Assert
    expect(badge.className).toContain("bg-status-failed");
    expect(badge.className).toContain("text-status-failed-foreground");
  });

  it("renders as an inline-flex span element", () => {
    // Arrange & Act
    render(<StatusBadge variant="active" />);
    const badge = screen.getByTestId("status-badge");

    // Assert
    expect(badge.tagName).toBe("SPAN");
    expect(badge.className).toContain("inline-flex");
  });
});

import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { JsonPayloadViewer } from "./JsonPayloadViewer";

describe("JsonPayloadViewer", () => {
  it("renders string values with quotes", () => {
    // Arrange & Act
    render(<JsonPayloadViewer payload={{ name: "hello" }} />);

    // Assert
    expect(screen.getByText('"hello"')).toBeInTheDocument();
  });

  it("renders number values", () => {
    // Arrange & Act
    render(<JsonPayloadViewer payload={{ count: 42 }} />);

    // Assert
    expect(screen.getByText("42")).toBeInTheDocument();
  });

  it("renders boolean values", () => {
    // Arrange & Act
    render(<JsonPayloadViewer payload={{ active: true }} />);

    // Assert
    expect(screen.getByText("true")).toBeInTheDocument();
  });

  it("renders null values", () => {
    // Arrange & Act
    render(<JsonPayloadViewer payload={{ nothing: null }} />);

    // Assert
    expect(screen.getByText("null")).toBeInTheDocument();
  });

  it("renders Copy JSON button", () => {
    // Arrange & Act
    render(<JsonPayloadViewer payload={{ key: "value" }} />);

    // Assert
    expect(
      screen.getByRole("button", { name: "Copy JSON" }),
    ).toBeInTheDocument();
  });

  it("renders Payload title", () => {
    // Arrange & Act
    render(<JsonPayloadViewer payload={{}} />);

    // Assert
    expect(screen.getByText("Payload")).toBeInTheDocument();
  });

  it("renders collapsible toggle buttons for nested objects", () => {
    // Arrange & Act
    render(
      <JsonPayloadViewer
        payload={{ nested: { inner: "value" } }}
        initialCollapsed={false}
      />,
    );

    // Assert — inner value should be visible
    expect(screen.getByText('"value"')).toBeInTheDocument();
    const toggleButtons = screen
      .getAllByRole("button")
      .filter(
        (buttonElement) =>
          buttonElement.textContent === "\u25BC" ||
          buttonElement.textContent === "\u25B6",
      );
    expect(toggleButtons.length).toBeGreaterThan(0);
  });

  it("starts collapsed when initialCollapsed is true", () => {
    // Arrange & Act
    render(
      <JsonPayloadViewer
        payload={{ nested: { inner: "value" } }}
        initialCollapsed={true}
      />,
    );

    // Assert — collapsed hint should show
    expect(screen.getByText(/1 keys/)).toBeInTheDocument();
  });
});

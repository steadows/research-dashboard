import { render, screen } from "@testing-library/react";
import { describe, it, expect } from "vitest";
import { HUDCard } from "@/components/ui/hud-card";

describe("HUDCard", () => {
  it("renders children", () => {
    render(<HUDCard>Card content</HUDCard>);
    expect(screen.getByText("Card content")).toBeInTheDocument();
  });

  it("renders title when provided", () => {
    render(<HUDCard title="System Status">Body</HUDCard>);
    expect(screen.getByText(/System Status/)).toBeInTheDocument();
  });

  it("renders index prefix with title", () => {
    render(<HUDCard index="[01]" title="Metrics">Body</HUDCard>);
    expect(screen.getByText(/\[01\].*Metrics/)).toBeInTheDocument();
  });

  it("renders meta in top-right area", () => {
    render(<HUDCard title="Test" meta="LIVE">Body</HUDCard>);
    expect(screen.getByText("LIVE")).toBeInTheDocument();
  });

  it("does not render header when no index, title, or meta", () => {
    const { container } = render(<HUDCard>Just children</HUDCard>);
    // Header div should not be present — only the outer div and children text
    const headerDivs = container.querySelectorAll(".mb-4");
    expect(headerDivs).toHaveLength(0);
  });

  it("applies custom className", () => {
    const { container } = render(
      <HUDCard className="custom-class">Body</HUDCard>
    );
    expect(container.firstChild).toHaveClass("custom-class");
  });

  it("does NOT render corner brackets", () => {
    const { container } = render(
      <HUDCard index="[01]" title="Test" meta="META">
        Content
      </HUDCard>
    );
    // Ensure no SVG or pseudo-element corner bracket patterns
    const svgs = container.querySelectorAll("svg");
    expect(svgs).toHaveLength(0);
    // No elements with "corner" or "bracket" in class names
    const allElements = container.querySelectorAll("*");
    for (const el of allElements) {
      expect(el.className.toString()).not.toMatch(/corner|bracket/i);
    }
  });
});

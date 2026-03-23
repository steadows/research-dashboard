import { render, screen } from "@testing-library/react";
import { describe, it, expect } from "vitest";
import { ContentPanel } from "@/components/layout/ContentPanel";

describe("ContentPanel", () => {
  it("renders children", () => {
    render(<ContentPanel>Panel content</ContentPanel>);
    expect(screen.getByText("Panel content")).toBeInTheDocument();
  });

  it("renders label when provided", () => {
    render(<ContentPanel label="SYSTEM STATUS">Body</ContentPanel>);
    // HUDBracket wraps label in "[ label ]" format
    expect(screen.getByText(/SYSTEM STATUS/)).toBeInTheDocument();
  });

  it("renders status when provided", () => {
    render(<ContentPanel status="ONLINE">Content</ContentPanel>);
    expect(screen.getByText("ONLINE")).toBeInTheDocument();
  });

  it("renders both label and status simultaneously", () => {
    render(
      <ContentPanel label="INTEL FEED" status="LIVE">
        Data
      </ContentPanel>
    );
    expect(screen.getByText(/INTEL FEED/)).toBeInTheDocument();
    expect(screen.getByText("LIVE")).toBeInTheDocument();
  });

  it("renders without label or status", () => {
    const { container } = render(<ContentPanel>Bare content</ContentPanel>);
    expect(container).toBeInTheDocument();
    expect(screen.getByText("Bare content")).toBeInTheDocument();
  });

  it("applies additional className to the outer wrapper", () => {
    const { container } = render(
      <ContentPanel className="extra-class">Children</ContentPanel>
    );
    // HUDBracket's outer div should carry the className
    expect(container.firstChild).toHaveClass("extra-class");
  });

  it("renders multiple children", () => {
    render(
      <ContentPanel>
        <span>First</span>
        <span>Second</span>
      </ContentPanel>
    );
    expect(screen.getByText("First")).toBeInTheDocument();
    expect(screen.getByText("Second")).toBeInTheDocument();
  });
});

import { render, screen } from "@testing-library/react";
import { describe, it, expect } from "vitest";
import { Badge } from "@/components/ui/badge";

describe("Badge", () => {
  it("renders label text", () => {
    render(<Badge>JournalClub</Badge>);
    expect(screen.getByText("JournalClub")).toBeInTheDocument();
  });

  it("applies default variant styles", () => {
    const { container } = render(<Badge>Default</Badge>);
    const badge = container.querySelector("span");
    expect(badge).toHaveClass("border");
    expect(badge).toHaveClass("uppercase");
  });

  it("applies journalclub variant", () => {
    const { container } = render(
      <Badge variant="journalclub">JC</Badge>
    );
    const badge = container.querySelector("span");
    expect(badge?.className).toContain("accent-green");
  });

  it("applies tldr variant", () => {
    const { container } = render(<Badge variant="tldr">TLDR</Badge>);
    const badge = container.querySelector("span");
    expect(badge?.className).toContain("accent-amber");
  });

  it("applies method variant", () => {
    const { container } = render(<Badge variant="method">Method</Badge>);
    const badge = container.querySelector("span");
    expect(badge?.className).toContain("purple");
  });

  it("applies tool variant", () => {
    const { container } = render(<Badge variant="tool">Tool</Badge>);
    const badge = container.querySelector("span");
    expect(badge?.className).toContain("accent-green");
  });

  it("applies instagram variant", () => {
    const { container } = render(
      <Badge variant="instagram">IG</Badge>
    );
    const badge = container.querySelector("span");
    expect(badge?.className).toContain("indigo");
  });

  it("merges custom className", () => {
    const { container } = render(
      <Badge className="ml-2">Styled</Badge>
    );
    const badge = container.querySelector("span");
    expect(badge).toHaveClass("ml-2");
  });
});

import { render, screen } from "@testing-library/react";
import { describe, it, expect } from "vitest";
import { MetricCard } from "@/components/ui/metric-card";

describe("MetricCard", () => {
  it("renders the value", () => {
    render(
      <MetricCard index="[01]" title="Papers" value={42} />
    );
    expect(screen.getByText("42")).toBeInTheDocument();
  });

  it("renders the title and index", () => {
    render(
      <MetricCard index="[02]" title="Tools" value={15} />
    );
    expect(screen.getByText(/\[02\].*Tools/)).toBeInTheDocument();
  });

  it("renders delta text when provided", () => {
    render(
      <MetricCard index="[01]" title="Count" value={10} delta="+3 this week" />
    );
    expect(screen.getByText("+3 this week")).toBeInTheDocument();
  });

  it("applies delta color class", () => {
    const { container } = render(
      <MetricCard
        index="[01]"
        title="Errors"
        value={5}
        delta="+2"
        deltaColor="red"
      />
    );
    const deltaEl = container.querySelector(".text-accent-red");
    expect(deltaEl).toBeInTheDocument();
    expect(deltaEl).toHaveTextContent("+2");
  });

  it("renders meta text in header", () => {
    render(
      <MetricCard index="[01]" title="Score" value={99} meta="LIVE" />
    );
    expect(screen.getByText("LIVE")).toBeInTheDocument();
  });

  it("does not render delta element when not provided", () => {
    const { container } = render(
      <MetricCard index="[01]" title="Count" value={7} />
    );
    // Only one element in the value row — the value span itself
    const valueRow = container.querySelector(".flex.items-baseline");
    expect(valueRow?.children).toHaveLength(1);
  });

  it("accepts string or number for value", () => {
    render(
      <MetricCard index="[01]" title="Rate" value="98.5%" />
    );
    expect(screen.getByText("98.5%")).toBeInTheDocument();
  });
});

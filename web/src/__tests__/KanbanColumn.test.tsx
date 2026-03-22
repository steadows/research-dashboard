import { render, screen } from "@testing-library/react";
import { describe, it, expect } from "vitest";
import { KanbanColumn } from "@/app/workbench/KanbanColumn";

describe("KanbanColumn", () => {
  it("renders column title for queued status", () => {
    render(
      <KanbanColumn status="queued" count={3}>
        <div>child</div>
      </KanbanColumn>
    );
    expect(screen.getByText("QUEUED")).toBeInTheDocument();
  });

  it("renders column title for researching status", () => {
    render(
      <KanbanColumn status="researching" count={1}>
        <div>child</div>
      </KanbanColumn>
    );
    expect(screen.getByText("RESEARCHING")).toBeInTheDocument();
  });

  it("renders column title for completed status", () => {
    render(
      <KanbanColumn status="completed" count={5}>
        <div>child</div>
      </KanbanColumn>
    );
    expect(screen.getByText("COMPLETED")).toBeInTheDocument();
  });

  it("renders zero-padded count badge", () => {
    render(
      <KanbanColumn status="queued" count={3}>
        <div>child</div>
      </KanbanColumn>
    );
    expect(screen.getByText("COUNT: 03")).toBeInTheDocument();
  });

  it("renders children cards", () => {
    render(
      <KanbanColumn status="queued" count={2}>
        <div data-testid="card-1">Card 1</div>
        <div data-testid="card-2">Card 2</div>
      </KanbanColumn>
    );
    expect(screen.getByTestId("card-1")).toBeInTheDocument();
    expect(screen.getByTestId("card-2")).toBeInTheDocument();
  });

  it("renders empty state with zero count", () => {
    const { container } = render(
      <KanbanColumn status="queued" count={0}>
        {/* no children */}
      </KanbanColumn>
    );
    expect(screen.getByText("COUNT: 00")).toBeInTheDocument();
    // The card container exists but has no card children
    const cardContainer = container.querySelectorAll(".flex.flex-col.gap-4");
    expect(cardContainer.length).toBeGreaterThan(0);
  });
});

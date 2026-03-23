import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, it, expect, vi } from "vitest";
import { WorkbenchCard } from "@/app/workbench/WorkbenchCard";
import type { WorkbenchEntry } from "@/app/workbench/types";

function makeEntry(overrides: Partial<WorkbenchEntry> = {}): WorkbenchEntry {
  return {
    key: "tool::TestTool",
    name: "TestTool",
    source_type: "tool",
    status: "queued",
    notes: "A test note",
    previous_status: null,
    added_at: null,
    verdict: null,
    pid: null,
    log_file: null,
    category: "IDE",
    source: "TLDR 2026-03-07",
    tags: "",
    url: "",
    ...overrides,
  };
}

/** Click the card to expand its drawer so action buttons become visible. */
async function expandCard(user: ReturnType<typeof userEvent.setup>) {
  const article = screen.getByRole("article");
  await user.click(article);
}

describe("WorkbenchCard", () => {
  it("renders entry name for queued card", () => {
    render(<WorkbenchCard entry={makeEntry()} />);
    expect(screen.getByText("TestTool")).toBeInTheDocument();
  });

  it("renders source type badge for queued card", () => {
    render(<WorkbenchCard entry={makeEntry({ source_type: "method" })} />);
    expect(screen.getByText("method")).toBeInTheDocument();
  });

  it("renders notes for queued card", () => {
    render(<WorkbenchCard entry={makeEntry({ notes: "Important note" })} />);
    expect(screen.getByText("Important note")).toBeInTheDocument();
  });

  it("renders START RESEARCH button for queued card when expanded", async () => {
    const user = userEvent.setup();
    render(<WorkbenchCard entry={makeEntry()} />);
    await expandCard(user);
    expect(
      screen.getByRole("button", { name: "START RESEARCH" })
    ).toBeInTheDocument();
  });

  it("fires onStartResearch with entry key", async () => {
    const user = userEvent.setup();
    const handler = vi.fn();
    render(
      <WorkbenchCard entry={makeEntry()} onStartResearch={handler} />
    );
    await expandCard(user);
    await user.click(screen.getByRole("button", { name: "START RESEARCH" }));
    expect(handler).toHaveBeenCalledWith("tool::TestTool");
  });

  it("renders ACTIVE_SCAN label for researching card", () => {
    render(
      <WorkbenchCard entry={makeEntry({ status: "researching" })} />
    );
    expect(screen.getByText("ACTIVE_SCAN")).toBeInTheDocument();
  });

  it("renders VIEW LOG button for researching card when expanded", async () => {
    const user = userEvent.setup();
    render(
      <WorkbenchCard entry={makeEntry({ status: "researching" })} />
    );
    await expandCard(user);
    expect(
      screen.getByRole("button", { name: "VIEW LOG" })
    ).toBeInTheDocument();
  });

  it("fires onViewLog with entry key", async () => {
    const user = userEvent.setup();
    const handler = vi.fn();
    render(
      <WorkbenchCard
        entry={makeEntry({ status: "researching" })}
        onViewLog={handler}
      />
    );
    await expandCard(user);
    await user.click(screen.getByRole("button", { name: "VIEW LOG" }));
    expect(handler).toHaveBeenCalledWith("tool::TestTool");
  });

  it("renders verdict badge for completed card", () => {
    render(
      <WorkbenchCard
        entry={makeEntry({
          status: "completed",
          verdict: "programmatic",
        })}
      />
    );
    expect(screen.getByText("programmatic")).toBeInTheDocument();
  });

  it("renders VIEW REPORT button for completed card when expanded", async () => {
    const user = userEvent.setup();
    render(
      <WorkbenchCard
        entry={makeEntry({ status: "completed", verdict: "manual" })}
      />
    );
    await expandCard(user);
    expect(
      screen.getByRole("button", { name: "VIEW REPORT" })
    ).toBeInTheDocument();
  });

  it("fires onViewReport with entry key", async () => {
    const user = userEvent.setup();
    const handler = vi.fn();
    render(
      <WorkbenchCard
        entry={makeEntry({ status: "completed", verdict: "manual" })}
        onViewReport={handler}
      />
    );
    await expandCard(user);
    await user.click(screen.getByRole("button", { name: "VIEW REPORT" }));
    expect(handler).toHaveBeenCalledWith("tool::TestTool");
  });
});

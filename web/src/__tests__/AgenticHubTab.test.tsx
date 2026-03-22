import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { SWRConfig } from "swr";
import type { InstagramPost } from "@/app/dashboard/types";

// Mock the hooks module
vi.mock("@/app/dashboard/hooks", () => ({
  useInstagramFeed: vi.fn(),
}));

// Mock apiMutate
vi.mock("@/lib/api", async (importOriginal) => {
  const orig = await importOriginal<typeof import("@/lib/api")>();
  return {
    ...orig,
    apiMutate: vi.fn().mockResolvedValue({ summary: "Test summary" }),
  };
});

import { AgenticHubTab } from "@/app/dashboard/AgenticHubTab";
import { useInstagramFeed } from "@/app/dashboard/hooks";

const mockPost: InstagramPost = {
  id: "1",
  account: "ai_digest",
  title: "GPT-5 Analysis",
  key_points: ["Point one", "Point two"],
  tags: ["ai", "llm"],
  timestamp: new Date().toISOString(),
  status: "new",
};

const mockAnalyzedPost: InstagramPost = {
  id: "2",
  account: "ml_daily",
  title: "Transformer Update",
  key_points: ["Key insight"],
  tags: ["transformers"],
  timestamp: new Date().toISOString(),
  status: "analyzed",
};

function renderWithSWR(ui: React.ReactNode) {
  return render(
    <SWRConfig value={{ provider: () => new Map() }}>
      {ui}
    </SWRConfig>
  );
}

beforeEach(() => {
  vi.clearAllMocks();
});

describe("AgenticHubTab", () => {
  it("renders AGENTIC HUB heading", () => {
    vi.mocked(useInstagramFeed).mockReturnValue({
      data: [mockPost],
      isLoading: false,
    } as ReturnType<typeof useInstagramFeed>);

    renderWithSWR(<AgenticHubTab />);
    expect(screen.getByText("AGENTIC HUB")).toBeInTheDocument();
  });

  it("renders intel cards with post titles", () => {
    vi.mocked(useInstagramFeed).mockReturnValue({
      data: [mockPost, mockAnalyzedPost],
      isLoading: false,
    } as ReturnType<typeof useInstagramFeed>);

    renderWithSWR(<AgenticHubTab />);
    expect(screen.getByText("GPT-5 Analysis")).toBeInTheDocument();
    expect(screen.getByText("Transformer Update")).toBeInTheDocument();
  });

  it("renders REFRESH FEED button", () => {
    vi.mocked(useInstagramFeed).mockReturnValue({
      data: [mockPost],
      isLoading: false,
    } as ReturnType<typeof useInstagramFeed>);

    renderWithSWR(<AgenticHubTab />);
    expect(
      screen.getByRole("button", { name: "REFRESH FEED" })
    ).toBeInTheDocument();
  });

  it("renders SUMMARIZE button for non-analyzed posts", () => {
    vi.mocked(useInstagramFeed).mockReturnValue({
      data: [mockPost],
      isLoading: false,
    } as ReturnType<typeof useInstagramFeed>);

    renderWithSWR(<AgenticHubTab />);
    expect(
      screen.getByRole("button", { name: "SUMMARIZE" })
    ).toBeInTheDocument();
  });

  it("renders WORKBENCH button for sending to workbench", () => {
    vi.mocked(useInstagramFeed).mockReturnValue({
      data: [mockPost],
      isLoading: false,
    } as ReturnType<typeof useInstagramFeed>);

    renderWithSWR(<AgenticHubTab />);
    expect(
      screen.getByRole("button", { name: "WORKBENCH" })
    ).toBeInTheDocument();
  });

  it("renders account filter buttons", () => {
    vi.mocked(useInstagramFeed).mockReturnValue({
      data: [mockPost, mockAnalyzedPost],
      isLoading: false,
    } as ReturnType<typeof useInstagramFeed>);

    renderWithSWR(<AgenticHubTab />);
    expect(screen.getByRole("button", { name: "ALL" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "ai_digest" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "ml_daily" })).toBeInTheDocument();
  });

  it("filters posts by account when filter button clicked", async () => {
    const user = userEvent.setup();
    vi.mocked(useInstagramFeed).mockReturnValue({
      data: [mockPost, mockAnalyzedPost],
      isLoading: false,
    } as ReturnType<typeof useInstagramFeed>);

    renderWithSWR(<AgenticHubTab />);
    await user.click(screen.getByRole("button", { name: "ai_digest" }));

    expect(screen.getByText("GPT-5 Analysis")).toBeInTheDocument();
    expect(screen.queryByText("Transformer Update")).not.toBeInTheDocument();
  });

  it("shows skeletons during loading", () => {
    vi.mocked(useInstagramFeed).mockReturnValue({
      data: undefined,
      isLoading: true,
    } as ReturnType<typeof useInstagramFeed>);

    renderWithSWR(<AgenticHubTab />);
    // Should still show the heading
    expect(screen.getByText("AGENTIC HUB")).toBeInTheDocument();
  });

  it("renders key points in intel cards", () => {
    vi.mocked(useInstagramFeed).mockReturnValue({
      data: [mockPost],
      isLoading: false,
    } as ReturnType<typeof useInstagramFeed>);

    renderWithSWR(<AgenticHubTab />);
    expect(screen.getByText("Point one")).toBeInTheDocument();
    expect(screen.getByText("Point two")).toBeInTheDocument();
  });
});

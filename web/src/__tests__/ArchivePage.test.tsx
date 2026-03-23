import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { SWRConfig } from "swr";

// Mock swr at the module level — the page uses useSWR directly
vi.mock("swr", async (importOriginal) => {
  const actual = await importOriginal<typeof import("swr")>();
  return {
    ...actual,
    default: vi.fn(),
  };
});

// Mock apiMutate — restore mutate from swr properly
vi.mock("@/lib/api", async (importOriginal) => {
  const orig = await importOriginal<typeof import("@/lib/api")>();
  return {
    ...orig,
    apiMutate: vi.fn().mockResolvedValue({}),
  };
});

// framer-motion stub — AnimatePresence + m.div
vi.mock("framer-motion", async (importOriginal) => {
  const actual = await importOriginal<typeof import("framer-motion")>();
  return {
    ...actual,
    AnimatePresence: ({ children }: { children: React.ReactNode }) => <>{children}</>,
    m: {
      div: ({ children, ...props }: React.HTMLAttributes<HTMLDivElement>) => (
        <div {...props}>{children}</div>
      ),
    },
    useReducedMotion: () => false,
  };
});

// FeedSkeleton stub
vi.mock("@/app/dashboard/Skeleton", () => ({
  FeedSkeleton: ({ count }: { count: number }) => (
    <div data-testid="feed-skeleton" aria-label={`${count} skeleton items`} />
  ),
}));

import useSWR from "swr";
import ArchivePage from "@/app/archive/page";

const mockToolItem = {
  key: "tool-axon",
  type: "tool",
  name: "Axon Code Intel",
  status: "dismissed",
  notes: "Very useful tool",
  category: "DevTools",
  source: "TLDR",
};

const mockMethodItem = {
  key: "method-rag",
  type: "method",
  name: "RAG Pipeline",
  status: "dismissed",
  notes: "For retrieval tasks",
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

describe("ArchivePage", () => {
  it("renders the Archive heading", () => {
    vi.mocked(useSWR).mockReturnValue({
      data: [],
      isLoading: false,
    } as ReturnType<typeof useSWR>);

    renderWithSWR(<ArchivePage />);
    expect(screen.getByText("Archive")).toBeInTheDocument();
  });

  it("renders the dismissed items subtitle", () => {
    vi.mocked(useSWR).mockReturnValue({
      data: [],
      isLoading: false,
    } as ReturnType<typeof useSWR>);

    renderWithSWR(<ArchivePage />);
    expect(
      screen.getByText("DISMISSED ITEMS — RESTORE TO RETURN TO ACTIVE FEEDS")
    ).toBeInTheDocument();
  });

  it("renders skeleton during loading", () => {
    vi.mocked(useSWR).mockReturnValue({
      data: undefined,
      isLoading: true,
    } as ReturnType<typeof useSWR>);

    renderWithSWR(<ArchivePage />);
    expect(screen.getByTestId("feed-skeleton")).toBeInTheDocument();
  });

  it("renders LOADING... in item count during load", () => {
    vi.mocked(useSWR).mockReturnValue({
      data: undefined,
      isLoading: true,
    } as ReturnType<typeof useSWR>);

    renderWithSWR(<ArchivePage />);
    expect(screen.getByText("LOADING...")).toBeInTheDocument();
  });

  it("renders empty archive message when no items", () => {
    vi.mocked(useSWR).mockReturnValue({
      data: [],
      isLoading: false,
    } as ReturnType<typeof useSWR>);

    renderWithSWR(<ArchivePage />);
    expect(
      screen.getByText("Archive is empty — dismissed items will appear here")
    ).toBeInTheDocument();
  });

  it("renders archived item names", () => {
    vi.mocked(useSWR).mockReturnValue({
      data: [mockToolItem, mockMethodItem],
      isLoading: false,
    } as ReturnType<typeof useSWR>);

    renderWithSWR(<ArchivePage />);
    expect(screen.getByText("Axon Code Intel")).toBeInTheDocument();
    expect(screen.getByText("RAG Pipeline")).toBeInTheDocument();
  });

  it("renders item count in header", () => {
    vi.mocked(useSWR).mockReturnValue({
      data: [mockToolItem, mockMethodItem],
      isLoading: false,
    } as ReturnType<typeof useSWR>);

    renderWithSWR(<ArchivePage />);
    expect(screen.getByText("2 ITEMS")).toBeInTheDocument();
  });

  it("renders TOOL badge for tool items", () => {
    vi.mocked(useSWR).mockReturnValue({
      data: [mockToolItem],
      isLoading: false,
    } as ReturnType<typeof useSWR>);

    renderWithSWR(<ArchivePage />);
    expect(screen.getByText("TOOL")).toBeInTheDocument();
  });

  it("renders METHOD badge for method items", () => {
    vi.mocked(useSWR).mockReturnValue({
      data: [mockMethodItem],
      isLoading: false,
    } as ReturnType<typeof useSWR>);

    renderWithSWR(<ArchivePage />);
    expect(screen.getByText("METHOD")).toBeInTheDocument();
  });

  it("renders type filter buttons when multiple types present", () => {
    vi.mocked(useSWR).mockReturnValue({
      data: [mockToolItem, mockMethodItem],
      isLoading: false,
    } as ReturnType<typeof useSWR>);

    renderWithSWR(<ArchivePage />);
    expect(screen.getByRole("button", { name: "ALL" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "tool" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "method" })).toBeInTheDocument();
  });

  it("does NOT render filter buttons when only one type present", () => {
    vi.mocked(useSWR).mockReturnValue({
      data: [mockToolItem],
      isLoading: false,
    } as ReturnType<typeof useSWR>);

    renderWithSWR(<ArchivePage />);
    expect(screen.queryByRole("button", { name: "ALL" })).not.toBeInTheDocument();
  });

  it("filters items when a type filter button is clicked", async () => {
    const user = userEvent.setup();
    vi.mocked(useSWR).mockReturnValue({
      data: [mockToolItem, mockMethodItem],
      isLoading: false,
    } as ReturnType<typeof useSWR>);

    renderWithSWR(<ArchivePage />);
    await user.click(screen.getByRole("button", { name: "tool" }));

    expect(screen.getByText("Axon Code Intel")).toBeInTheDocument();
    expect(screen.queryByText("RAG Pipeline")).not.toBeInTheDocument();
  });

  it("filter button hides items not matching the selected type", async () => {
    const user = userEvent.setup();
    vi.mocked(useSWR).mockReturnValue({
      data: [
        mockToolItem,
        { key: "paper-1", type: "paper", name: "Paper Alpha", status: "dismissed" },
      ],
      isLoading: false,
    } as ReturnType<typeof useSWR>);

    renderWithSWR(<ArchivePage />);
    // Click "paper" filter — only paper items should remain
    await user.click(screen.getByRole("button", { name: "paper" }));
    expect(screen.queryByText("Axon Code Intel")).not.toBeInTheDocument();
    expect(screen.getByText("Paper Alpha")).toBeInTheDocument();
  });
});

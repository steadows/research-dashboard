import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, it, expect, vi, beforeEach } from "vitest";

// Mock the reports hooks before the page is imported
vi.mock("@/app/reports/hooks", () => ({
  useReports: vi.fn(),
  useReportContent: vi.fn(),
}));

// framer-motion: LazyMotion + m.div require a real motion renderer.
// Stub them to simple wrappers so AnimatePresence doesn't stall tests.
vi.mock("framer-motion", async (importOriginal) => {
  const actual = await importOriginal<typeof import("framer-motion")>();
  return {
    ...actual,
    LazyMotion: ({ children }: { children: React.ReactNode }) => <>{children}</>,
    domAnimation: undefined,
    m: {
      div: ({ children, ...props }: React.HTMLAttributes<HTMLDivElement>) => (
        <div {...props}>{children}</div>
      ),
    },
  };
});

import ReportsPage from "@/app/reports/page";
import { useReports, useReportContent } from "@/app/reports/hooks";
import type { ReportMeta } from "@/app/reports/hooks";

const mockReport: ReportMeta = {
  slug: "tldr-2025-01",
  title: "TLDR Weekly Digest",
  source_type: "tool",
  researched: "2025-01-06",
  excerpt: "AI tools roundup for the week.",
  has_html: false,
};

const mockReport2: ReportMeta = {
  slug: "journalclub-2025-01",
  title: "JournalClub Research Summary",
  source_type: "method",
  researched: "2025-01-07",
  excerpt: "Latest ML methods covered.",
  has_html: true,
};

beforeEach(() => {
  vi.clearAllMocks();
  // Default: no content loading
  vi.mocked(useReportContent).mockReturnValue({
    data: undefined,
    isLoading: false,
    error: undefined,
  } as any);
});

describe("ReportsPage", () => {
  it("renders the Reports heading", () => {
    vi.mocked(useReports).mockReturnValue({
      data: [],
      isLoading: false,
      error: undefined,
    } as any);

    render(<ReportsPage />);
    expect(screen.getByText("Reports")).toBeInTheDocument();
  });

  it("renders the /Research_Library subtitle", () => {
    vi.mocked(useReports).mockReturnValue({
      data: [],
      isLoading: false,
      error: undefined,
    } as any);

    render(<ReportsPage />);
    expect(screen.getByText("/Research_Library")).toBeInTheDocument();
  });

  it("renders loading skeletons while fetching", () => {
    vi.mocked(useReports).mockReturnValue({
      data: undefined,
      isLoading: true,
      error: undefined,
    } as any);

    const { container } = render(<ReportsPage />);
    const skeletons = container.querySelectorAll(".animate-pulse");
    expect(skeletons.length).toBeGreaterThan(0);
  });

  it("renders empty state when reports list is empty", () => {
    vi.mocked(useReports).mockReturnValue({
      data: [],
      isLoading: false,
      error: undefined,
    } as any);

    render(<ReportsPage />);
    expect(screen.getByText("NO REPORTS GENERATED")).toBeInTheDocument();
  });

  it("renders error message on fetch failure", () => {
    vi.mocked(useReports).mockReturnValue({
      data: undefined,
      isLoading: false,
      error: new Error("Network error"),
    } as any);

    render(<ReportsPage />);
    expect(
      screen.getByText("Failed to load reports. Check API connection.")
    ).toBeInTheDocument();
  });

  it("renders report cards when data is loaded", () => {
    vi.mocked(useReports).mockReturnValue({
      data: [mockReport, mockReport2],
      isLoading: false,
      error: undefined,
    } as any);

    render(<ReportsPage />);
    expect(screen.getByText("TLDR Weekly Digest")).toBeInTheDocument();
    expect(screen.getByText("JournalClub Research Summary")).toBeInTheDocument();
  });

  it("renders report count when data is loaded", () => {
    vi.mocked(useReports).mockReturnValue({
      data: [mockReport, mockReport2],
      isLoading: false,
      error: undefined,
    } as any);

    render(<ReportsPage />);
    expect(screen.getByText("2 REPORTS")).toBeInTheDocument();
  });

  it("renders HTML badge for reports with has_html=true", () => {
    vi.mocked(useReports).mockReturnValue({
      data: [mockReport2],
      isLoading: false,
      error: undefined,
    } as any);

    render(<ReportsPage />);
    expect(screen.getByText("HTML")).toBeInTheDocument();
  });

  it("renders report date string", () => {
    vi.mocked(useReports).mockReturnValue({
      data: [mockReport],
      isLoading: false,
      error: undefined,
    } as any);

    render(<ReportsPage />);
    expect(screen.getByText("2025-01-06")).toBeInTheDocument();
  });

  it("renders report excerpt text", () => {
    vi.mocked(useReports).mockReturnValue({
      data: [mockReport],
      isLoading: false,
      error: undefined,
    } as any);

    render(<ReportsPage />);
    expect(screen.getByText("AI tools roundup for the week.")).toBeInTheDocument();
  });

  it("selecting a report card shows the content viewer", async () => {
    const user = userEvent.setup();
    vi.mocked(useReports).mockReturnValue({
      data: [mockReport],
      isLoading: false,
      error: undefined,
    } as any);
    vi.mocked(useReportContent).mockReturnValue({
      data: { slug: "tldr-2025-01", content: "# Report content here" },
      isLoading: false,
      error: undefined,
    } as any);

    render(<ReportsPage />);
    await user.click(screen.getByText("TLDR Weekly Digest"));

    // After selection, the slug should appear in the viewer toolbar
    expect(screen.getByText("tldr-2025-01")).toBeInTheDocument();
  });

  it("clicking selected report again deselects it", async () => {
    const user = userEvent.setup();
    vi.mocked(useReports).mockReturnValue({
      data: [mockReport],
      isLoading: false,
      error: undefined,
    } as any);
    vi.mocked(useReportContent).mockReturnValue({
      data: { slug: "tldr-2025-01", content: "Content" },
      isLoading: false,
      error: undefined,
    } as any);

    render(<ReportsPage />);
    const card = screen.getByText("TLDR Weekly Digest");
    await user.click(card);
    await user.click(card);

    // Viewer toolbar slug should no longer be present
    expect(screen.queryByText("OPEN IN NEW TAB")).not.toBeInTheDocument();
  });
});

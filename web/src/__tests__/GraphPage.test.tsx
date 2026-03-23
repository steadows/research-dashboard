import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, it, expect, vi, beforeEach } from "vitest";

// Mock the dashboard hooks used by GraphInsightsTab
vi.mock("@/app/dashboard/hooks", () => ({
  useGraphHealth: vi.fn(),
  useGraphCommunities: vi.fn(),
  useHubNotes: vi.fn(),
}));

// Skeleton stub
vi.mock("@/app/dashboard/Skeleton", () => ({
  Skeleton: ({ className }: { className?: string }) => (
    <div data-testid="skeleton" className={className} />
  ),
}));

// DataReadout stub — renders label + value as text
vi.mock("@/components/ui/data-readout", () => ({
  DataReadout: ({
    label,
    value,
  }: {
    label: string;
    value: string | number;
  }) => (
    <div>
      <span>{label}</span>
      <span>{value}</span>
    </div>
  ),
}));

import GraphPage from "@/app/graph/page";
import { useGraphHealth, useGraphCommunities, useHubNotes } from "@/app/dashboard/hooks";

const mockHealth = {
  total_nodes: 42,
  total_edges: 87,
  connected_components: 3,
  orphan_nodes: 2,
  avg_degree: 4.14,
  density: 0.0498,
};

beforeEach(() => {
  vi.clearAllMocks();
  // Default: no communities or hub notes
  vi.mocked(useGraphCommunities).mockReturnValue({
    data: undefined,
    isLoading: false,
  } as ReturnType<typeof useGraphCommunities>);
  vi.mocked(useHubNotes).mockReturnValue({
    data: undefined,
    isLoading: false,
  } as ReturnType<typeof useHubNotes>);
});

describe("GraphPage", () => {
  it("renders the Graph heading", () => {
    vi.mocked(useGraphHealth).mockReturnValue({
      data: undefined,
      isLoading: true,
    } as ReturnType<typeof useGraphHealth>);

    render(<GraphPage />);
    expect(screen.getByText("Graph")).toBeInTheDocument();
  });

  it("renders the /Knowledge_Network subtitle", () => {
    vi.mocked(useGraphHealth).mockReturnValue({
      data: undefined,
      isLoading: true,
    } as ReturnType<typeof useGraphHealth>);

    render(<GraphPage />);
    expect(screen.getByText("/Knowledge_Network")).toBeInTheDocument();
  });

  it("renders the description line", () => {
    vi.mocked(useGraphHealth).mockReturnValue({
      data: undefined,
      isLoading: true,
    } as ReturnType<typeof useGraphHealth>);

    render(<GraphPage />);
    expect(
      screen.getByText("Vault Graph Health & Community Intelligence")
    ).toBeInTheDocument();
  });

  it("renders Graph Insights heading from inner component", () => {
    vi.mocked(useGraphHealth).mockReturnValue({
      data: undefined,
      isLoading: false,
    } as ReturnType<typeof useGraphHealth>);

    render(<GraphPage />);
    expect(screen.getByText("Graph Insights")).toBeInTheDocument();
  });

  it("renders loading skeletons while fetching", () => {
    vi.mocked(useGraphHealth).mockReturnValue({
      data: undefined,
      isLoading: true,
    } as ReturnType<typeof useGraphHealth>);

    const { container } = render(<GraphPage />);
    const skeletons = container.querySelectorAll("[data-testid='skeleton']");
    expect(skeletons.length).toBeGreaterThan(0);
  });

  it("renders metric labels when data is loaded", () => {
    vi.mocked(useGraphHealth).mockReturnValue({
      data: mockHealth,
      isLoading: false,
    } as ReturnType<typeof useGraphHealth>);

    render(<GraphPage />);
    expect(screen.getByText("TOTAL NODES")).toBeInTheDocument();
    expect(screen.getByText("TOTAL EDGES")).toBeInTheDocument();
    expect(screen.getByText("COMPONENTS")).toBeInTheDocument();
    expect(screen.getByText("ORPHAN NODES")).toBeInTheDocument();
  });

  it("renders metric values from health data", () => {
    vi.mocked(useGraphHealth).mockReturnValue({
      data: mockHealth,
      isLoading: false,
    } as ReturnType<typeof useGraphHealth>);

    render(<GraphPage />);
    expect(screen.getByText("42")).toBeInTheDocument();
    expect(screen.getByText("87")).toBeInTheDocument();
  });

  it("renders hub notes table when hub notes are present", () => {
    vi.mocked(useGraphHealth).mockReturnValue({
      data: mockHealth,
      isLoading: false,
    } as ReturnType<typeof useGraphHealth>);
    vi.mocked(useHubNotes).mockReturnValue({
      data: [
        { name: "AI Project", pagerank: 0.0812, in_degree: 15, betweenness: 0.0031 },
      ],
      isLoading: false,
    } as ReturnType<typeof useHubNotes>);

    render(<GraphPage />);
    expect(screen.getByText(/HUB NOTES/)).toBeInTheDocument();
    expect(screen.getByText("AI Project")).toBeInTheDocument();
  });

  it("renders communities section when communities are present", async () => {
    const user = userEvent.setup();
    vi.mocked(useGraphHealth).mockReturnValue({
      data: mockHealth,
      isLoading: false,
    } as ReturnType<typeof useGraphHealth>);
    vi.mocked(useGraphCommunities).mockReturnValue({
      data: [["Note A", "Note B", "Note C"], ["Note D", "Note E", "Note F"]],
      isLoading: false,
    } as ReturnType<typeof useGraphCommunities>);

    render(<GraphPage />);
    expect(screen.getByText(/COMMUNITIES/)).toBeInTheDocument();
    expect(screen.getByText("Community 1")).toBeInTheDocument();

    // Expand community 1 to see members
    await user.click(screen.getByText("Community 1"));
    expect(screen.getByText("Note A")).toBeInTheDocument();
  });
});

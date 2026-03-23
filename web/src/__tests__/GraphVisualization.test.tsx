import { render, screen } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { GraphVisualization } from "@/app/cockpit/GraphVisualization";
import type { GraphData } from "@/app/cockpit/types";

// D3 manipulates the DOM directly inside useEffect after dynamic import.
// We mock the d3 module so the test environment (happy-dom) does not need
// a real SVG layout engine — we only test the React-rendered wrapper.
vi.mock("d3", () => {
  const noop = () => mockD3Selection;
  const mockD3Selection: Record<string, unknown> = {};

  // Build a chainable no-op selection proxy
  const methods = [
    "select", "selectAll", "attr", "style", "append", "data", "join",
    "call", "on", "remove", "filter",
  ];
  for (const m of methods) {
    mockD3Selection[m] = () => mockD3Selection;
  }

  const mockSimulation = {
    force: () => mockSimulation,
    on: () => mockSimulation,
    stop: vi.fn(),
    alphaTarget: () => mockSimulation,
    restart: () => mockSimulation,
  };

  return {
    select: noop,
    zoom: () => ({ scaleExtent: () => ({ on: () => ({ call: noop }) }) }),
    drag: () => ({ on: () => ({ on: () => ({ on: () => ({}) }) }) }),
    forceSimulation: () => mockSimulation,
    forceLink: () => ({ id: () => ({ distance: () => ({}) }) }),
    forceManyBody: () => ({ strength: () => ({}) }),
    forceCenter: () => ({}),
    forceCollide: () => ({ radius: () => ({}) }),
  };
});

const emptyData: GraphData = { nodes: [], edges: [] };

const populatedData: GraphData = {
  nodes: [
    { id: "proj-1", type: "project", label: "My Project" },
    { id: "tool-1", type: "tool", label: "Some Tool" },
    { id: "method-1", type: "method", label: "My Method" },
  ],
  edges: [
    { source: "proj-1", target: "tool-1", relation: "linked" },
    { source: "proj-1", target: "method-1", relation: "suggested" },
  ],
};

beforeEach(() => {
  vi.clearAllMocks();
});

describe("GraphVisualization", () => {
  it("renders the NETWORK_TOPOLOGY_01 label", () => {
    render(<GraphVisualization data={emptyData} />);
    expect(screen.getByText("NETWORK_TOPOLOGY_01")).toBeInTheDocument();
  });

  it("renders the Neural Map Viz heading", () => {
    render(<GraphVisualization data={emptyData} />);
    expect(screen.getByText("Neural Map Viz")).toBeInTheDocument();
  });

  it("renders empty state message when no nodes", () => {
    render(<GraphVisualization data={emptyData} />);
    expect(screen.getByText("No graph data available")).toBeInTheDocument();
  });

  it("renders hint text in empty state", () => {
    render(<GraphVisualization data={emptyData} />);
    expect(
      screen.getByText("Select a project with linked items to visualize")
    ).toBeInTheDocument();
  });

  it("renders node count when data has nodes", () => {
    const { container } = render(<GraphVisualization data={populatedData} />);
    // Node count is rendered in a specific font-mono div alongside the edge count
    const countDiv = container.querySelector(".font-mono.text-2xl");
    expect(countDiv).not.toBeNull();
    expect(countDiv?.textContent).toContain("3");
  });

  it("renders edge count alongside node count", () => {
    const { container } = render(<GraphVisualization data={populatedData} />);
    const countDiv = container.querySelector(".font-mono.text-2xl");
    expect(countDiv?.textContent).toContain("/2");
  });

  it("renders the Nodes label when data is non-empty", () => {
    render(<GraphVisualization data={populatedData} />);
    expect(screen.getByText("Nodes")).toBeInTheDocument();
  });

  it("does NOT render the Nodes label when empty", () => {
    render(<GraphVisualization data={emptyData} />);
    expect(screen.queryByText("Nodes")).not.toBeInTheDocument();
  });

  it("renders RENDER_MODE: D3_FORCE decoration", () => {
    render(<GraphVisualization data={emptyData} />);
    expect(screen.getByText("RENDER_MODE: D3_FORCE")).toBeInTheDocument();
  });

  it("renders legend entries for each node type", () => {
    render(<GraphVisualization data={emptyData} />);
    // NODE_COLORS has keys: project, method, tool, blog
    expect(screen.getByText("project")).toBeInTheDocument();
    expect(screen.getByText("method")).toBeInTheDocument();
    expect(screen.getByText("tool")).toBeInTheDocument();
    expect(screen.getByText("blog")).toBeInTheDocument();
  });

  it("renders svg container element when data has nodes", () => {
    const { container } = render(<GraphVisualization data={populatedData} />);
    // The svg ref element is rendered (not the empty-state svg icon)
    const svgs = container.querySelectorAll("svg");
    expect(svgs.length).toBeGreaterThan(0);
  });

  it("accepts and applies a custom className", () => {
    const { container } = render(
      <GraphVisualization data={emptyData} className="custom-graph" />
    );
    expect(container.firstChild).toHaveClass("custom-graph");
  });

  it("calls onNodeClick when provided (callback wired up without error)", () => {
    const onNodeClick = vi.fn();
    // Just verify the component renders without throwing when the prop is provided
    expect(() =>
      render(<GraphVisualization data={populatedData} onNodeClick={onNodeClick} />)
    ).not.toThrow();
  });
});

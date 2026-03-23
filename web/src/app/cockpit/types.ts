/** Cockpit page types — shared across cockpit components */

// ─── API Response Types ─────────────────────────────────────────────────────

export interface Project {
  name: string;
  status: string;
  domain: string;
  tech: string[];
  overview: string;
  source_dir?: string;
}

export interface ProjectItem {
  title: string;
  source: string;
  type: "method" | "tool" | "blog";
  status: string;
  discovery_source?: string;
  relevance_score?: number;
}

export interface GraphNode {
  id: string;
  type: "project" | "method" | "tool" | "blog";
  label: string;
}

export interface GraphEdge {
  source: string;
  target: string;
  relation: "linked" | "community" | "suggested";
}

export interface GraphData {
  nodes: GraphNode[];
  edges: GraphEdge[];
}

export interface AnalysisResult {
  analysis: string;
  model: string;
  tokens_used: number;
  cached: boolean;
}

// ─── D3 Simulation Types ────────────────────────────────────────────────────

export interface SimNode extends d3.SimulationNodeDatum {
  id: string;
  type: GraphNode["type"];
  label: string;
}

export interface SimEdge extends d3.SimulationLinkDatum<SimNode> {
  relation: GraphEdge["relation"];
}

// ─── Color / Style Constants ────────────────────────────────────────────────

export const NODE_COLORS: Record<GraphNode["type"], string> = {
  project: "#06B6D4",
  method: "#A855F7",
  tool: "#22C55E",
  blog: "#F59E0B",
} as const;

export const EDGE_STYLES: Record<GraphEdge["relation"], { color: string; dasharray: string }> = {
  linked: { color: "#06B6D4", dasharray: "" },
  community: { color: "#3B82F6", dasharray: "" },
  suggested: { color: "#F59E0B", dasharray: "4 2" },
} as const;

export const NODE_RADIUS: Record<GraphNode["type"], number> = {
  project: 10,
  method: 6,
  tool: 6,
  blog: 6,
} as const;

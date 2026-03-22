/** API response types for dashboard data */

export interface DashboardStats {
  papers: number;
  tools: number;
  blog_queue: number;
  active_projects: number;
}

export interface BlogItem {
  title: string;
  status: string;
  category?: string;
  tags?: string[];
  source?: string;
  notes?: string;
}

export interface ToolItem {
  name: string;
  category?: string;
  status?: string;
  source?: string;
  url?: string;
  notes?: string;
  tags?: string[];
}

export interface MethodItem {
  name: string;
  category?: string;
  status?: string;
  source?: string;
  paper_url?: string;
  notes?: string;
  tags?: string[];
}

export interface ReportItem {
  title: string;
  date: string;
  source: string;
  type: "journalclub" | "tldr";
  highlights?: string[];
  file_path?: string;
}

export interface GraphHealth {
  total_nodes: number;
  total_edges: number;
  connected_components: number;
  orphan_nodes: number;
  avg_degree: number;
  density: number;
}

export interface InstagramPost {
  id: string;
  account: string;
  title: string;
  key_points: string[];
  transcript_excerpt?: string;
  tags: string[];
  timestamp: string;
  status?: string;
}

export interface WorkbenchItem {
  id: string;
  title: string;
  type: string;
  status: string;
  source?: string;
}

/** Tab identifiers for the dashboard */
export type DashboardTab =
  | "home"
  | "blog-queue"
  | "tools-radar"
  | "research-archive"
  | "ai-signal"
  | "graph-insights"
  | "agentic-hub";

export const DASHBOARD_TABS: { id: DashboardTab; label: string }[] = [
  { id: "home", label: "HOME" },
  { id: "blog-queue", label: "BLOG QUEUE" },
  { id: "tools-radar", label: "TOOLS RADAR" },
  { id: "research-archive", label: "RESEARCH ARCHIVE" },
  { id: "ai-signal", label: "AI SIGNAL" },
  { id: "graph-insights", label: "GRAPH INSIGHTS" },
  { id: "agentic-hub", label: "AGENTIC HUB" },
];

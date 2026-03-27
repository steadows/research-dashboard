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
  hook?: string;
  source_paper?: string;
  projects?: string[];
  added?: string;
}

export interface ToolItem {
  name: string;
  category?: string;
  status?: string;
  source?: string;
  url?: string;
  notes?: string;
  summary?: string;
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

/** Structured brief extracted per report — same shape as HomeSummary. */
export type ReportBrief = HomeSummary;

export interface ReportItem {
  title: string;
  date: string;
  source: string;
  type: "journalclub" | "tldr";
  brief: ReportBrief;
  /** @deprecated Kept during additive migration — use brief instead. */
  highlights?: string[];
  /** @deprecated Kept during additive migration — use brief instead. */
  summary?: string;
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

export interface PaperItem {
  title: string;
  report_date: string;
  authors: string | null;
  year: string | null;
  link: string | null;
  snippet: string | null;
  synthesis: string | null;
  relevance: string | null;
  relevance_level: "High" | "Medium" | "Low" | "None" | null;
  blog_potential: string | null;
  project_applications: string[];
}

export interface HomeSummary {
  top_picks: string[];
  top_tools: { name: string; category: string }[];
  blog_ideas: { title: string; status: string }[];
  ai_signal: string | null;
  ai_signal_source: string | null;
}

/** Tab identifiers for the dashboard */
export type DashboardTab =
  | "home"
  | "blog-queue"
  | "tools-radar"
  | "research-archive";

export const DASHBOARD_TABS: { id: DashboardTab; label: string }[] = [
  { id: "home", label: "HOME" },
  { id: "blog-queue", label: "BLOG QUEUE" },
  { id: "tools-radar", label: "TOOLS RADAR" },
  { id: "research-archive", label: "RESEARCH ARCHIVE" },
];

/** Workbench pipeline types */

/** Backend pipeline statuses */
export type BackendStatus =
  | "queued"
  | "researching"
  | "researched"
  | "sandbox_creating"
  | "sandbox_ready"
  | "experiment_running"
  | "experiment_done"
  | "manual"
  | "failed"
  | "completed";

/** Kanban column keys */
export type KanbanColumn = "queued" | "researching" | "completed";

/** Status used on entries — keeps the backend status for rendering */
export type WorkbenchStatus = BackendStatus;

export type SourceType = "tool" | "method" | "instagram";

export type Verdict = "programmatic" | "manual" | null;

export interface WorkbenchEntry {
  /** Namespaced key from API, e.g. "tool::ItemName" */
  key: string;
  /** Display name */
  name: string;
  /** Source type — determines badge color */
  source_type: SourceType;
  /** Pipeline status — determines column placement */
  status: WorkbenchStatus;
  /** Freeform notes / description */
  notes: string;
  /** Previous status before current */
  previous_status: string | null;
  /** ISO timestamp when item was added */
  added_at: string | null;
  /** Research verdict (completed items only) */
  verdict: Verdict;
  /** Process ID if research is running */
  pid: number | null;
  /** Path to research log file */
  log_file: string | null;
  /** Category (e.g. "LLM Framework", "Data Pipeline") */
  category: string;
  /** Discovery source (e.g. "tldr", "journalclub") */
  source: string;
  /** Comma-separated tags or tag string */
  tags: string;
  /** URL for tool homepage or paper */
  url: string;
  /** Method description / "why it matters" */
  description?: string;
  /** Paper URL (methods only) */
  paper_url?: string;
  /** Key points (instagram only) */
  key_points?: string[];
  /** Keywords (instagram only) */
  keywords?: string[];
  /** Post caption (instagram only) */
  caption?: string;
  /** Instagram account handle */
  account?: string;
  /** Instagram shortcode */
  shortcode?: string;
  /** Associated project names */
  projects?: string[];
  /** Path to vault note (if published to Obsidian) */
  vault_note?: string;
  /** Whether experiment design has been reviewed */
  reviewed?: boolean;
  /** Whether research flagged potential costs */
  cost_flagged?: boolean;
  /** Cost/subscription details from research */
  cost_notes?: string;
  /** Whether user acknowledged costs */
  cost_approved?: boolean;
  /** Path to sandbox output directory */
  sandbox_dir?: string | null;
  /** Path to experiment findings */
  findings_path?: string | null;
}

/** API response shape — dict keyed by namespaced key */
export type WorkbenchApiResponse = Record<
  string,
  Omit<WorkbenchEntry, "key">
>;

/** Grouped entries by kanban column */
export interface WorkbenchColumns {
  queued: WorkbenchEntry[];
  researching: WorkbenchEntry[];
  completed: WorkbenchEntry[];
}

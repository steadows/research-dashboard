/** Workbench pipeline types */

export type WorkbenchStatus = "queued" | "researching" | "completed";

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
}

/** API response shape — dict keyed by namespaced key */
export type WorkbenchApiResponse = Record<
  string,
  Omit<WorkbenchEntry, "key">
>;

/** Grouped entries by status for kanban display */
export interface WorkbenchColumns {
  queued: WorkbenchEntry[];
  researching: WorkbenchEntry[];
  completed: WorkbenchEntry[];
}

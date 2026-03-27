import useSWR from "swr";
import { defaultSWRConfig, apiMutate } from "@/lib/api";
import type {
  WorkbenchApiResponse,
  WorkbenchColumns,
  WorkbenchEntry,
  WorkbenchStatus,
  KanbanColumn,
} from "./types";

/** Map backend statuses to kanban columns */
const STATUS_TO_COLUMN: Record<string, KanbanColumn> = {
  queued: "queued",
  researching: "researching",
  researched: "completed",
  sandbox_creating: "completed",
  sandbox_ready: "completed",
  experiment_running: "completed",
  experiment_done: "completed",
  manual: "completed",
  failed: "completed",
  completed: "completed",
};

/** Parse API dict response into grouped columns — preserves backend status */
function groupByStatus(data: WorkbenchApiResponse): WorkbenchColumns {
  const columns: WorkbenchColumns = {
    queued: [],
    researching: [],
    completed: [],
  };

  for (const [key, entry] of Object.entries(data)) {
    const column = STATUS_TO_COLUMN[entry.status] ?? "queued";
    const item: WorkbenchEntry = { ...entry, key };

    columns[column].push(item);
  }

  return columns;
}

/** SWR hook for workbench data — fetches and groups by status */
export function useWorkbench() {
  const { data, error, isLoading, mutate } = useSWR<WorkbenchApiResponse>(
    "/workbench",
    {
      ...defaultSWRConfig,
      refreshInterval: 10_000,
    }
  );

  const columns: WorkbenchColumns = data
    ? groupByStatus(data)
    : { queued: [], researching: [], completed: [] };

  return { columns, error, isLoading, mutate };
}

/** Transition an item to a new status via PATCH */
export async function updateWorkbenchStatus(
  key: string,
  status: WorkbenchStatus
): Promise<void> {
  await apiMutate(`/workbench/${encodeURIComponent(key)}`, {
    method: "PATCH",
    body: { updates: { status } },
  });
}

/** Launch the research agent for a workbench item via POST */
export async function launchResearch(key: string): Promise<void> {
  await apiMutate(`/research/launch/${encodeURIComponent(key)}`, {
    method: "POST",
  });
}

/** Fetch the Experiment Design section from research.md */
export async function fetchExperimentDesign(
  key: string
): Promise<string> {
  const url = `/api/research/experiment-design/${encodeURIComponent(key)}`;
  const res = await fetch(url);
  if (!res.ok) {
    const body = await res.text().catch(() => "");
    throw new Error(`Failed to fetch experiment design (${res.status}): ${body}`);
  }
  const data: { content: string } = await res.json();
  return data.content;
}

/** Mark an item as reviewed (gate step 1) */
export async function markReviewed(key: string): Promise<void> {
  await apiMutate(`/workbench/${encodeURIComponent(key)}`, {
    method: "PATCH",
    body: { updates: { reviewed: true } },
  });
}

/** Acknowledge cost warning (gate step 2) */
export async function acknowledgeCost(key: string): Promise<void> {
  await apiMutate(`/workbench/${encodeURIComponent(key)}`, {
    method: "PATCH",
    body: { updates: { cost_approved: true } },
  });
}

/** Run the experiment (docker run via run.sh) */
export async function runExperiment(key: string): Promise<void> {
  await apiMutate(`/research/run-experiment/${encodeURIComponent(key)}`, {
    method: "POST",
  });
}

/** Fetch experiment results and findings */
export async function fetchExperimentResults(
  key: string
): Promise<{
  results: Record<string, unknown> | null;
  findings: string | null;
  log_tail: string;
  completed: boolean;
}> {
  const url = `/api/research/experiment-results/${encodeURIComponent(key)}`;
  const res = await fetch(url);
  if (!res.ok) throw new Error(`Failed (${res.status})`);
  return res.json();
}

/** Kill a running experiment */
export async function killExperiment(key: string): Promise<void> {
  await apiMutate(`/research/kill-experiment/${encodeURIComponent(key)}`, {
    method: "POST",
  });
}

/** Launch the sandbox agent for a completed research item via POST */
export async function launchSandbox(key: string): Promise<void> {
  await apiMutate(`/research/sandbox/${encodeURIComponent(key)}`, {
    method: "POST",
  });
}

/** Remove an item from the workbench (restores previous status) */
export async function removeFromWorkbench(key: string): Promise<void> {
  await apiMutate(`/workbench/${encodeURIComponent(key)}`, {
    method: "DELETE",
  });
}

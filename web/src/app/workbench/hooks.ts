import useSWR from "swr";
import { defaultSWRConfig, apiMutate } from "@/lib/api";
import type {
  WorkbenchApiResponse,
  WorkbenchColumns,
  WorkbenchEntry,
  WorkbenchStatus,
} from "./types";

/** Parse API dict response into grouped columns */
function groupByStatus(data: WorkbenchApiResponse): WorkbenchColumns {
  const columns: WorkbenchColumns = {
    queued: [],
    researching: [],
    completed: [],
  };

  for (const [key, entry] of Object.entries(data)) {
    const status = entry.status as WorkbenchStatus;
    const item: WorkbenchEntry = { ...entry, key };

    if (status in columns) {
      columns[status].push(item);
    }
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

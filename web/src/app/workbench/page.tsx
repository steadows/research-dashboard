"use client";

import { useCallback, useState } from "react";
import { apiMutate } from "@/lib/api";
import {
  useWorkbench,
  launchResearch,
  updateWorkbenchStatus,
  removeFromWorkbench,
} from "./hooks";
import { KanbanColumn } from "./KanbanColumn";
import { WorkbenchCard } from "./WorkbenchCard";
import { ResearchLog } from "./ResearchLog";
import { WorkbenchSkeleton } from "./Skeleton";
import type { WorkbenchStatus } from "./types";

/**
 * Workbench page — Kanban pipeline view for research items.
 * Three columns: QUEUED -> RESEARCHING -> COMPLETED.
 */
export default function WorkbenchPage() {
  const { columns, isLoading, error, mutate } = useWorkbench();
  const [expandedLogs, setExpandedLogs] = useState<Set<string>>(new Set());

  const handleStartResearch = useCallback(
    async (key: string) => {
      // Launch the actual research agent, then update status
      await launchResearch(key);
      // Auto-expand the log for the item that just started
      setExpandedLogs((prev) => new Set([...prev, key]));
      mutate();
    },
    [mutate]
  );

  const handleViewLog = useCallback((key: string) => {
    setExpandedLogs((prev) => {
      const next = new Set(prev);
      if (next.has(key)) {
        next.delete(key);
      } else {
        next.add(key);
      }
      return next;
    });
  }, []);

  const handleResearchComplete = useCallback(
    async (key: string) => {
      // Transition item to completed status
      await updateWorkbenchStatus(key, "completed");
      // Refetch workbench data — card will move to completed column
      mutate();
      // Collapse the log after completion
      setExpandedLogs((prev) => {
        const next = new Set(prev);
        next.delete(key);
        return next;
      });
    },
    [mutate]
  );

  const handleRemove = useCallback(
    async (key: string) => {
      await removeFromWorkbench(key);
      mutate();
    },
    [mutate]
  );

  const handleViewReport = useCallback((key: string) => {
    const reportUrl = `/api/research/report/${encodeURIComponent(key)}`;
    window.open(reportUrl, "_blank", "noopener,noreferrer");
  }, []);

  const handlePublishVault = useCallback(
    async (key: string) => {
      try {
        const result = await apiMutate<{ obsidian_uri: string; vault_note: string }>(
          `/research/publish-vault/${encodeURIComponent(key)}`,
          { method: "POST" }
        );
        // Open in Obsidian via URI scheme
        window.open(result.obsidian_uri, "_self");
        mutate();
      } catch (err) {
        console.error("Publish to vault failed:", err);
      }
    },
    [mutate]
  );

  return (
    <div className="pb-8">
      {/* Page header */}
      <div className="mb-10 flex flex-col gap-4 md:flex-row md:items-end md:justify-between">
        <div>
          <h1 className="flex items-baseline gap-3 font-heading text-4xl font-black uppercase tracking-tighter text-accent-cyan">
            Workbench
            <span className="text-sm font-mono font-normal text-text-muted">
              /Pipeline_v2.04
            </span>
          </h1>
          <p className="mt-1 font-mono text-xs uppercase text-text-muted">
            Mission Control Research Pipeline
          </p>
        </div>
      </div>

      {/* Error state */}
      {error && (
        <div className="mb-6 border border-accent-red/30 bg-accent-red/5 p-4 font-mono text-xs text-accent-red">
          Failed to load workbench data. Check API connection.
        </div>
      )}

      {/* Loading skeleton */}
      {isLoading && <WorkbenchSkeleton />}

      {/* Empty state */}
      {!isLoading &&
        !error &&
        columns.queued.length === 0 &&
        columns.researching.length === 0 &&
        columns.completed.length === 0 && (
          <div className="border border-outline-variant/30 bg-bg-surface p-8 text-center">
            <p className="font-mono text-sm text-text-secondary mb-2">
              NO ITEMS IN PIPELINE
            </p>
            <p className="font-mono text-xs text-text-muted">
              Send items from Tools Radar, AI Signal, or Agentic Hub to start
              researching.
            </p>
          </div>
        )}

      {/* Kanban board */}
      {!isLoading && (
        <div className="grid grid-cols-1 gap-6 items-start lg:grid-cols-3">
          {(["queued", "researching", "completed"] as WorkbenchStatus[]).map(
            (status) => (
              <KanbanColumn
                key={status}
                status={status}
                count={columns[status].length}
              >
                {columns[status].map((entry) => (
                  <div
                    key={entry.key}
                    className="flex flex-col gap-3"
                    role="listitem"
                  >
                    <WorkbenchCard
                      entry={entry}
                      onStartResearch={handleStartResearch}
                      onViewLog={handleViewLog}
                      onViewReport={handleViewReport}
                      onPublishVault={handlePublishVault}
                      onRemove={handleRemove}
                    />
                    {entry.status === "researching" && (
                      <ResearchLog
                        itemKey={entry.key}
                        isActive={expandedLogs.has(entry.key)}
                        onComplete={() => handleResearchComplete(entry.key)}
                      />
                    )}
                  </div>
                ))}
              </KanbanColumn>
            )
          )}
        </div>
      )}
    </div>
  );
}

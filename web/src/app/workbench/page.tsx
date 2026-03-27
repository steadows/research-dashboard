"use client";

import { useCallback, useState } from "react";
import { m, AnimatePresence, useReducedMotion } from "framer-motion";
import { apiMutate } from "@/lib/api";
import {
  useWorkbench,
  launchResearch,
  launchSandbox,
  updateWorkbenchStatus,
  removeFromWorkbench,
} from "./hooks";
import { KanbanColumn } from "./KanbanColumn";
import { WorkbenchCard } from "./WorkbenchCard";
import { ResearchLog } from "./ResearchLog";
import { WorkbenchSkeleton } from "./Skeleton";
import type { KanbanColumn as KanbanColumnType } from "./types";

/**
 * Workbench page — Kanban pipeline view for research items.
 * Three columns: QUEUED -> RESEARCHING -> COMPLETED.
 */
export default function WorkbenchPage() {
  const { columns, isLoading, error, mutate } = useWorkbench();
  const [expandedLogs, setExpandedLogs] = useState<Set<string>>(new Set());
  const [focusedKey, setFocusedKey] = useState<string | null>(null);
  const reduceMotion = useReducedMotion();

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

  const handleStartSandbox = useCallback(
    async (key: string) => {
      try {
        await launchSandbox(key);
        mutate();
      } catch (err) {
        console.error("Sandbox launch failed:", err);
      }
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

      {/* Focused card — full-width above kanban with slide-from-right + expand-down */}
      <AnimatePresence mode="wait">
        {!isLoading && focusedKey && (() => {
          const allEntries = [...columns.queued, ...columns.researching, ...columns.completed];
          const focusedEntry = allEntries.find((e) => e.key === focusedKey);
          if (!focusedEntry) return null;
          return (
            <m.div
              key={focusedEntry.key}
              initial={{ x: "60%", scaleY: 0.6, opacity: 0, transformOrigin: "top right" }}
              animate={{ x: 0, scaleY: 1, opacity: 1, transformOrigin: "top right" }}
              exit={{ x: "60%", scaleY: 0.6, opacity: 0, transformOrigin: "top right" }}
              transition={
                reduceMotion
                  ? { duration: 0 }
                  : {
                      type: "spring",
                      stiffness: 260,
                      damping: 28,
                      mass: 0.8,
                      opacity: { duration: 0.25 },
                    }
              }
              className="mb-8"
            >
              <WorkbenchCard
                entry={focusedEntry}
                focused
                onStartResearch={handleStartResearch}
                onStartSandbox={handleStartSandbox}
                onViewLog={handleViewLog}
                onViewReport={handleViewReport}
                onPublishVault={handlePublishVault}
                onRemove={handleRemove}
                onCollapse={() => setFocusedKey(null)}
              />
            </m.div>
          );
        })()}
      </AnimatePresence>

      {/* Kanban board — dims when a card is focused */}
      {!isLoading && (
        <m.div
          animate={
            focusedKey
              ? { opacity: 0.5, scale: 0.98, filter: "blur(1px)" }
              : { opacity: 1, scale: 1, filter: "blur(0px)" }
          }
          transition={
            reduceMotion
              ? { duration: 0 }
              : { type: "spring", stiffness: 300, damping: 30 }
          }
          className="grid grid-cols-1 gap-6 items-start lg:grid-cols-3"
        >
          {(["queued", "researching", "completed"] as KanbanColumnType[]).map(
            (status) => (
              <KanbanColumn
                key={status}
                status={status}
                count={columns[status].length}
              >
                {columns[status]
                  .filter((entry) => entry.key !== focusedKey)
                  .map((entry) => (
                  <div
                    key={entry.key}
                    className="flex flex-col gap-3"
                    role="listitem"
                  >
                    <WorkbenchCard
                      entry={entry}
                      onStartResearch={handleStartResearch}
                      onStartSandbox={handleStartSandbox}
                      onViewLog={handleViewLog}
                      onViewReport={handleViewReport}
                      onPublishVault={handlePublishVault}
                      onRemove={handleRemove}
                      onFocus={setFocusedKey}
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
        </m.div>
      )}
    </div>
  );
}

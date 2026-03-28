"use client";

import { useState, useCallback } from "react";
import { useLinkerStatus } from "./hooks";
import { apiMutate } from "@/lib/api";

// Map internal step names to user-friendly labels
const DIRECTORY_LABELS: Record<string, string> = {
  Satellites: "Project Links",
};

function friendlyName(dir: string): string {
  return DIRECTORY_LABELS[dir] ?? dir;
}

export function KnowledgeLinkerCard() {
  const { data: status, mutate } = useLinkerStatus();
  const [dismissed, setDismissed] = useState(false);

  const handleRun = useCallback(async () => {
    setDismissed(false);
    try {
      await apiMutate("/linker/run", { method: "POST" });
      // Start polling by revalidating
      mutate();
    } catch (err: unknown) {
      // 409 = already running — just start polling
      if (err instanceof Error && err.message.includes("409")) {
        mutate();
        return;
      }
      // Surface unexpected errors by revalidating — the status
      // endpoint will reflect any server-side error state
      console.error("Linker run failed:", err);
      mutate();
    }
  }, [mutate]);

  const isIdle = !status || status.status === "idle";
  const isRunning = status?.status === "running";
  const isComplete =
    status?.status === "complete" || status?.status === "partial";
  const isError = status?.status === "error";
  const isPartial = status?.status === "partial";

  // Check for stale "running" state (>30s)
  const isStale =
    isRunning &&
    status?.started_at != null &&
    Date.now() - new Date(status.started_at).getTime() > 30_000;

  return (
    <div className="bg-bg-surface border border-accent-cyan/20 p-5 rounded-none">
      <div className="flex items-center justify-between mb-4">
        <h3 className="font-headline text-accent-cyan uppercase tracking-widest text-sm">
          Knowledge Linker
        </h3>
        {isRunning && (
          <div className="flex items-center gap-2 text-xs text-text-secondary">
            <span className="inline-block w-2 h-2 rounded-full bg-accent-cyan animate-pulse" />
            {status?.current_directory
              ? `Linking ${friendlyName(status.current_directory)}…`
              : "Starting…"}
          </div>
        )}
      </div>

      {/* Action button */}
      {(isIdle || (isComplete && dismissed) || isError) && (
        <button
          onClick={handleRun}
          className="px-4 py-2 bg-accent-cyan/10 border border-accent-cyan/30 text-accent-cyan hover:bg-accent-cyan/20 transition-colors text-sm font-mono uppercase tracking-wider"
        >
          Link Vault
        </button>
      )}

      {/* Running state */}
      {isRunning && !isStale && (
        <div className="text-xs text-text-secondary font-mono">
          Processing vault directories…
        </div>
      )}

      {/* Stale warning */}
      {isStale && (
        <div className="text-xs text-amber-400 font-mono">
          Run may have failed — started over 30s ago.{" "}
          <button
            onClick={handleRun}
            className="underline hover:text-amber-300"
          >
            Retry
          </button>
        </div>
      )}

      {/* Results */}
      {isComplete && !dismissed && (
        <div
          className={`mt-3 p-3 border text-sm font-mono ${
            isPartial
              ? "border-amber-500/30 bg-amber-500/5"
              : "border-green-500/30 bg-green-500/5"
          }`}
        >
          <div className="flex items-center gap-2 mb-2">
            <span>{isPartial ? "⚠" : "✓"}</span>
            <span className={isPartial ? "text-amber-400" : "text-green-400"}>
              {status?.total_modified ?? 0} files modified
            </span>
          </div>

          {/* Per-directory breakdown */}
          {status?.results && (
            <div className="space-y-1 text-xs text-text-secondary">
              {Object.entries(status.results)
                .filter(([, count]) => count > 0)
                .map(([dir, count]) => (
                  <div key={dir} className="flex justify-between">
                    <span>{friendlyName(dir)}</span>
                    <span>{count}</span>
                  </div>
                ))}
            </div>
          )}

          {/* Warnings */}
          {isPartial && status?.warnings && status.warnings.length > 0 && (
            <div className="mt-2 text-xs text-amber-400">
              {status.warnings.map((w, i) => (
                <div key={i}>⚠ {w}</div>
              ))}
            </div>
          )}

          <button
            onClick={() => setDismissed(true)}
            className="mt-3 text-xs text-text-secondary hover:text-text-primary uppercase tracking-wider"
          >
            Dismiss
          </button>
        </div>
      )}

      {/* Error */}
      {isError && (
        <div className="mt-3 p-3 border border-red-500/30 bg-red-500/5 text-sm font-mono text-red-400">
          {status?.error ?? "Unknown error"}
          <button
            onClick={handleRun}
            className="ml-3 underline hover:text-red-300"
          >
            Retry
          </button>
        </div>
      )}
    </div>
  );
}

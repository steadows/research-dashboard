"use client";

import { useState, useMemo, useCallback, useEffect } from "react";
import { mutate as swrMutate } from "swr";
import { cn } from "@/lib/utils";
import { GlowButton } from "@/components/ui/glow-button";
import { apiMutate } from "@/lib/api";
import type { ProjectItem } from "./types";

interface ItemsFeedProps {
  items: ProjectItem[];
  isLoading: boolean;
  /** Project dict for per-item analysis calls */
  project?: { name: string } | null;
}

type FilterType = "all" | "method" | "tool" | "blog";

const TYPE_STYLES: Record<string, { border: string; accent: string; label: string }> = {
  method: {
    border: "border-l-purple",
    accent: "text-purple",
    label: "METHOD",
  },
  tool: {
    border: "border-l-accent-green",
    accent: "text-accent-green",
    label: "TOOL",
  },
  blog: {
    border: "border-l-accent-amber",
    accent: "text-accent-amber",
    label: "BLOG",
  },
};

/**
 * ItemsFeed — Single-item navigator with Prev/Next for stepping through
 * flagged items per project. Filterable by type. Per-item Analyze/Go Deep.
 */
export function ItemsFeed({ items, isLoading, project }: ItemsFeedProps) {
  const [filter, setFilter] = useState<FilterType>("all");
  const [currentIdx, setCurrentIdx] = useState(0);

  const filtered = useMemo(() => {
    if (filter === "all") return items;
    return items.filter((item) => item.type === filter);
  }, [items, filter]);

  // Reset index when filter or items change
  useEffect(() => {
    setCurrentIdx(0);
  }, [filter, items]);

  if (isLoading) {
    return (
      <div className="py-12 text-center">
        <div className="inline-block h-4 w-4 animate-pulse bg-accent-cyan/30" />
        <p className="mt-2 font-mono text-[10px] text-outline/50">
          LOADING_ITEMS...
        </p>
      </div>
    );
  }

  if (items.length === 0) {
    return (
      <div className="py-12 text-center">
        <p className="font-mono text-xs uppercase text-outline/50">
          No linked items found
        </p>
      </div>
    );
  }

  const filterButtons: { value: FilterType; label: string }[] = [
    { value: "all", label: "ALL" },
    { value: "method", label: "METHODS" },
    { value: "tool", label: "TOOLS" },
    { value: "blog", label: "BLOG" },
  ];

  const safeIdx = Math.min(currentIdx, Math.max(0, filtered.length - 1));
  const currentItem = filtered[safeIdx] ?? null;

  return (
    <div className="space-y-5">
      {/* Filter bar + count */}
      <div className="flex items-center justify-between">
        <div className="flex gap-2">
          {filterButtons.map((btn) => (
            <button
              key={btn.value}
              onClick={() => setFilter(btn.value)}
              className={cn(
                "px-3 py-1 font-mono text-[10px] uppercase tracking-wider transition-all duration-75",
                filter === btn.value
                  ? "border border-accent-cyan bg-accent-cyan/10 text-accent-cyan"
                  : "border border-outline-variant/30 text-outline hover:text-accent-cyan"
              )}
            >
              {btn.label}
            </button>
          ))}
        </div>
        <span className="font-mono text-[10px] text-outline/50">
          {filtered.length} item{filtered.length !== 1 ? "s" : ""}
        </span>
      </div>

      {filtered.length === 0 ? (
        <div className="py-8 text-center">
          <p className="font-mono text-xs uppercase text-outline/50">
            No items match filter
          </p>
        </div>
      ) : (
        <>
          {/* Navigator */}
          <div className="flex items-center gap-4">
            <button
              onClick={() => setCurrentIdx((i) => Math.max(0, i - 1))}
              disabled={safeIdx === 0}
              className="border border-outline-variant/30 px-3 py-1 font-mono text-[10px] uppercase text-outline transition-colors hover:text-accent-cyan disabled:opacity-30"
            >
              PREV
            </button>
            <div className="flex-1 text-center font-mono text-[10px] text-outline/60">
              {safeIdx + 1} of {filtered.length}
            </div>
            <button
              onClick={() => setCurrentIdx((i) => Math.min(filtered.length - 1, i + 1))}
              disabled={safeIdx >= filtered.length - 1}
              className="border border-outline-variant/30 px-3 py-1 font-mono text-[10px] uppercase text-outline transition-colors hover:text-accent-cyan disabled:opacity-30"
            >
              NEXT
            </button>
          </div>

          {/* Current item */}
          {currentItem && (
            <ItemCard key={currentItem.title} item={currentItem} project={project} />
          )}
        </>
      )}
    </div>
  );
}

// ─── Sub-components ─────────────────────────────────────────────────────────

interface AnalysisResult {
  analysis: string;
  model: string;
  tokens_used: number;
  cached: boolean;
}

interface ItemCardProps {
  item: ProjectItem;
  project?: { name: string; source_dir?: string } | null;
}

function ItemCard({ item, project }: ItemCardProps) {
  const style = TYPE_STYLES[item.type] ?? TYPE_STYLES.method;
  const [wbStatus, setWbStatus] = useState<"idle" | "sending" | "sent">("idle");
  const [dismissing, setDismissing] = useState(false);
  const [analysisResult, setAnalysisResult] = useState<AnalysisResult | null>(null);
  const [analyzing, setAnalyzing] = useState<"quick" | "deep" | null>(null);
  const [analyzeError, setAnalyzeError] = useState<string | null>(null);

  const handleWorkbench = useCallback(async () => {
    if (wbStatus !== "idle") return;
    setWbStatus("sending");
    try {
      await apiMutate("/workbench", {
        body: {
          item: {
            source_type: item.type,
            name: item.title,
            category: "",
            status: "",
            source: item.discovery_source,
            notes: "",
            tags: "",
            projects: project ? [project.name] : [],
            project_name: project?.name ?? "",
            project_dir: project?.source_dir ?? "",
          },
        },
      });
      await swrMutate("/workbench");
      setWbStatus("sent");
      setTimeout(() => setWbStatus("idle"), 2000);
    } catch (err) {
      console.error("Workbench send failed:", err);
      setWbStatus("idle");
    }
  }, [item, wbStatus]);

  const handleDismiss = useCallback(async () => {
    if (dismissing) return;
    setDismissing(true);
    const key = `${item.type}::${item.title}`;
    try {
      await apiMutate(`/status/${key}`, { body: { status: "dismissed" } });
      await swrMutate("/cockpit/items");
    } catch (err) {
      console.error("Dismiss failed:", err);
      setDismissing(false);
    }
  }, [item.type, item.title, dismissing]);

  const handleAnalyze = useCallback(async (mode: "quick" | "deep") => {
    if (analyzing || !project) return;
    setAnalyzing(mode);
    setAnalyzeError(null);
    try {
      const endpoint = mode === "quick" ? "/analyze" : "/analyze/deep";
      const result = await apiMutate<AnalysisResult>(endpoint, {
        body: {
          item: { name: item.title, source_type: item.type },
          project: { name: project.name },
        },
      });
      setAnalysisResult(result);
    } catch (err) {
      const msg = err instanceof Error ? err.message : "Analysis failed";
      setAnalyzeError(msg);
      console.error(`${mode} analysis failed:`, err);
    } finally {
      setAnalyzing(null);
    }
  }, [item.title, item.type, project, analyzing]);

  return (
    <div
      className={cn(
        "border-l-4 bg-bg-surface p-5 space-y-4",
        style.border
      )}
    >
      {/* Header */}
      <div className="flex items-start justify-between gap-3">
        <div className="space-y-1">
          <div className="flex items-center gap-2">
            <span className={cn("font-mono text-[9px] uppercase tracking-widest", style.accent)}>
              {style.label}
            </span>
            <span className="font-mono text-[9px] text-outline/40">
              {(item.discovery_source ?? "").toUpperCase()}
            </span>
          </div>
          <h3 className="font-heading text-lg font-bold uppercase tracking-tight text-white">
            {item.title}
          </h3>
        </div>
      </div>

      {/* Relevance bar */}
      {item.relevance_score != null && (
        <div className="flex items-center gap-4">
          <div className="h-1.5 flex-1 overflow-hidden bg-outline-variant/20">
            <div
              className={cn("h-full transition-all", style.border.replace("border-l-", "bg-"))}
              style={{ width: `${item.relevance_score}%` }}
            />
          </div>
          <span className={cn("font-mono text-[10px]", style.accent)}>
            {item.relevance_score}% MATCH
          </span>
        </div>
      )}

      {/* Actions — always visible */}
      <div className="flex flex-wrap gap-2 pt-2">
        {project && (
          <>
            <GlowButton
              variant="secondary"
              className="py-2 px-4 text-[10px]"
              onClick={() => handleAnalyze("quick")}
              disabled={analyzing !== null}
            >
              {analyzing === "quick" ? "ANALYZING..." : "ANALYZE"}
            </GlowButton>
            <button
              onClick={() => handleAnalyze("deep")}
              disabled={analyzing !== null}
              className="bg-accent-amber text-bg-base px-4 py-2 font-heading text-[10px] font-bold uppercase tracking-widest transition-all hover:brightness-110 disabled:opacity-50"
            >
              {analyzing === "deep" ? "DEEP SCAN..." : "GO DEEP"}
            </button>
          </>
        )}
        <button
          onClick={handleWorkbench}
          disabled={wbStatus !== "idle"}
          className={cn(
            "border px-3 py-2 font-heading text-[10px] font-bold uppercase tracking-widest transition-colors disabled:opacity-50",
            wbStatus === "sent"
              ? "border-accent-green bg-accent-green text-bg-base"
              : "border-outline-variant/30 text-outline hover:text-accent-cyan"
          )}
        >
          {wbStatus === "sent" ? "SENT" : wbStatus === "sending" ? "..." : "WORKBENCH"}
        </button>
        <GlowButton
          variant="secondary"
          className="py-2 px-3 text-[10px]"
          onClick={handleDismiss}
          disabled={dismissing}
        >
          {dismissing ? "..." : "DISMISS"}
        </GlowButton>
      </div>

      {/* Analysis error */}
      {analyzeError && (
        <div className="border border-accent-red/30 bg-accent-red/5 p-3">
          <p className="font-mono text-xs text-accent-red">{analyzeError}</p>
        </div>
      )}

      {/* Analysis result */}
      {analysisResult && (
        <div className="space-y-2 border border-outline-variant/10 bg-bg-base p-4">
          <div className="flex items-center gap-3 border-b border-outline-variant/10 pb-2">
            <span className="font-mono text-[9px] text-outline">
              {analysisResult.model.toUpperCase()}
            </span>
            <span className="font-mono text-[9px] text-outline">
              {analysisResult.tokens_used.toLocaleString()} tokens
            </span>
            {analysisResult.cached && (
              <span className="border border-accent-green/30 bg-accent-green/10 px-1.5 py-0.5 font-mono text-[8px] text-accent-green">
                CACHED
              </span>
            )}
          </div>
          <div className="max-h-80 overflow-y-auto">
            <p className="whitespace-pre-wrap font-sans text-xs leading-relaxed text-text-secondary">
              {analysisResult.analysis}
            </p>
          </div>
        </div>
      )}
    </div>
  );
}

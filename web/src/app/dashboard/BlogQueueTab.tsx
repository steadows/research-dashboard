"use client";

import { useState, useCallback, useEffect } from "react";
import { mutate as swrMutate } from "swr";
import { AnimatePresence, m, useReducedMotion } from "framer-motion";
import { Badge } from "@/components/ui/badge";
import { GlowButton } from "@/components/ui/glow-button";
import { apiMutate } from "@/lib/api";
import { useBlogQueue } from "./hooks";
import { FeedSkeleton } from "./Skeleton";
import type { BlogItem } from "./types";

type BlogFilter = "all" | "Idea" | "Draft" | "Review";

/** Strip markdown headings (e.g. "# The Quick Version\n\n") from LLM output. */
function stripLeadingHeading(text: string): string {
  return text.replace(/^#+\s+.*\n+/, "").trim();
}

/** Read/write LLM results to sessionStorage so they survive page navigation. */
function getCached(key: string): string | null {
  try { return sessionStorage.getItem(key); } catch { return null; }
}
function setCached(key: string, value: string): void {
  try { sessionStorage.setItem(key, value); } catch { /* quota exceeded */ }
}

/** Build the item payload for blog queue API calls. */
function blogItemPayload(item: BlogItem) {
  return {
    name: item.title,
    hook: item.hook ?? "",
    "source paper": item.source_paper ?? "",
    source: item.source ?? "",
    tags: item.tags?.join(", ") ?? "",
  };
}

function BlogCard({ item, index }: { item: BlogItem; index: number }) {
  const reduceMotion = useReducedMotion();
  const cachePrefix = `blog::${item.title}::`;
  const [expanded, setExpanded] = useState(false);
  const [summary, setSummary] = useState<string | null>(() => getCached(`${cachePrefix}summary`));
  const [summarizing, setSummarizing] = useState(false);
  const [deepRead, setDeepRead] = useState<string | null>(() => getCached(`${cachePrefix}deepRead`));
  const [deepReading, setDeepReading] = useState(false);
  const [analysis, setAnalysis] = useState<string | null>(() => getCached(`${cachePrefix}analysis`));
  const [analyzing, setAnalyzing] = useState(false);
  const [draft, setDraft] = useState<string | null>(() => getCached(`${cachePrefix}draft`));
  const [drafting, setDrafting] = useState(false);
  const [dismissing, setDismissing] = useState(false);

  // Auto-fetch summary when card is expanded
  useEffect(() => {
    if (!expanded || summary || summarizing) return;
    let cancelled = false;
    setSummarizing(true);
    apiMutate<{ summary: string }>(
      "/blog-queue/summarize",
      { body: { item: blogItemPayload(item) } }
    )
      .then((result) => {
        if (!cancelled) {
          setSummary(result.summary);
          setCached(`${cachePrefix}summary`, result.summary);
        }
      })
      .catch((err) => console.error("Summarize failed:", err))
      .finally(() => { if (!cancelled) setSummarizing(false); });
    return () => { cancelled = true; };
  }, [expanded, item, summary, summarizing, cachePrefix]);

  const handleDeepRead = useCallback(async (e: React.MouseEvent) => {
    e.stopPropagation();
    if (deepReading || deepRead) return;
    setDeepReading(true);
    try {
      const result = await apiMutate<{ deep_read: string }>(
        "/blog-queue/deep-read",
        { body: { item: blogItemPayload(item) } }
      );
      setDeepRead(result.deep_read);
      setCached(`${cachePrefix}deepRead`, result.deep_read);
    } catch (err) {
      console.error("Deep read failed:", err);
    } finally {
      setDeepReading(false);
    }
  }, [item, deepRead, deepReading, cachePrefix]);

  const handleAnalyze = useCallback(async (e: React.MouseEvent) => {
    e.stopPropagation();
    if (analyzing || analysis) return;
    setAnalyzing(true);
    try {
      const result = await apiMutate<{ analysis: string }>(
        "/blog-queue/analyze",
        { body: { item: blogItemPayload(item) } }
      );
      setAnalysis(result.analysis);
      setCached(`${cachePrefix}analysis`, result.analysis);
    } catch (err) {
      console.error("Analysis failed:", err);
    } finally {
      setAnalyzing(false);
    }
  }, [item, analysis, analyzing, cachePrefix]);

  const handleDismiss = useCallback(async (e: React.MouseEvent) => {
    e.stopPropagation();
    if (dismissing) return;
    setDismissing(true);
    try {
      await apiMutate(`/status/blog::${item.title}`, { body: { status: "dismissed" } });
      await swrMutate("/blog-queue");
    } catch (err) {
      console.error("Dismiss failed:", err);
      setDismissing(false);
    }
  }, [item.title, dismissing]);

  const handleGenerateDraft = useCallback(async (e: React.MouseEvent) => {
    e.stopPropagation();
    if (drafting || draft) return;
    setDrafting(true);
    try {
      const result = await apiMutate<{ draft: string; draft_path: string }>(
        "/blog-queue/draft",
        { body: { item: blogItemPayload(item) } }
      );
      setDraft(result.draft);
      setCached(`${cachePrefix}draft`, result.draft);
    } catch (err) {
      console.error("Draft generation failed:", err);
    } finally {
      setDrafting(false);
    }
  }, [item, draft, drafting, cachePrefix]);

  const statusColor =
    item.status === "Draft"
      ? "text-accent-amber"
      : item.status === "Review"
        ? "text-accent-green"
        : "text-outline";

  return (
    <div
      className="bg-bg-surface border-l-4 border-accent-amber hover:box-glow-amber group transition-all duration-200 cursor-pointer"
      onClick={() => setExpanded((v) => !v)}
    >
      {/* Header — always visible */}
      <div className="p-5 pb-3 space-y-2">
        <div className="flex justify-between items-start gap-3">
          <div className="flex items-center gap-2 min-w-0">
            <span className="font-mono text-[10px] text-accent-cyan/50 shrink-0">
              [{String(index + 1).padStart(2, "0")}]
            </span>
            <h3 className="font-mono font-bold text-sm text-white group-hover:text-accent-cyan transition-colors truncate">
              {item.title}
            </h3>
          </div>
          <span className={`font-headline text-[9px] uppercase tracking-wider shrink-0 ${statusColor}`}>
            {item.status?.toUpperCase() ?? "IDEA"}
          </span>
        </div>

        {/* Hook — visible at a glance */}
        {item.hook && (
          <p className="font-mono text-[11px] text-text-secondary italic leading-relaxed border-l-2 border-accent-amber/30 pl-3 ">
            {item.hook}
          </p>
        )}

        {/* Tags — visible at a glance */}
        {item.tags && item.tags.length > 0 && (
          <div className="flex flex-wrap gap-1.5 ">
            {item.tags.map((tag) => (
              <span
                key={tag}
                className="text-[9px] font-mono border border-accent-cyan/40 text-accent-cyan px-2 py-0.5"
              >
                {tag.toUpperCase()}
              </span>
            ))}
          </div>
        )}
      </div>

      {/* Hover-reveal drawer */}
      <AnimatePresence>
        {expanded && (
          <m.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: "auto", opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={
              reduceMotion
                ? { duration: 0 }
                : { height: { type: "spring", stiffness: 500, damping: 30 }, opacity: { duration: 0.2 } }
            }
            className="overflow-hidden"
          >
            <div className="px-5 pb-5 space-y-3">
              {/* Source Paper */}
              {item.source_paper && (
                <div>
                  <p className="text-[10px] font-headline font-bold text-accent-cyan/70 uppercase tracking-[0.2em] mb-1">
                    Source Paper
                  </p>
                  <p className="font-mono text-[11px] text-text-primary leading-relaxed">
                    {item.source_paper}
                  </p>
                </div>
              )}

              {/* Projects */}
              {item.projects && item.projects.length > 0 && (
                <div className="flex flex-wrap gap-1.5">
                  {item.projects.map((proj) => (
                    <span
                      key={proj}
                      className="text-[9px] font-mono border border-accent-green/40 text-accent-green bg-accent-green/10 px-2 py-0.5"
                    >
                      {proj}
                    </span>
                  ))}
                </div>
              )}

              {/* Date added */}
              {item.added && (
                <p className="font-mono text-[9px] text-outline">
                  Added {item.added}
                </p>
              )}

              {/* Quick Summary — auto-loaded */}
              {summarizing && (
                <p className="font-mono text-[10px] text-accent-cyan/50 animate-pulse">
                  Summarizing...
                </p>
              )}
              {summary && (
                <div className="bg-bg-base border border-accent-cyan/20 p-3 text-xs text-text-secondary leading-relaxed max-h-40 overflow-y-auto whitespace-pre-wrap">
                  {stripLeadingHeading(summary)}
                </div>
              )}

              {/* Deep Read result */}
              {deepRead && (
                <div className="space-y-1">
                  <p className="text-[10px] font-headline font-bold text-accent-green/70 uppercase tracking-[0.2em]">
                    Deep Read
                  </p>
                  <div className="bg-bg-base border border-accent-green/20 p-3 text-xs text-text-secondary leading-relaxed max-h-60 overflow-y-auto whitespace-pre-wrap">
                    {stripLeadingHeading(deepRead)}
                  </div>
                </div>
              )}

              {/* Analysis result */}
              {analysis && (
                <div className="space-y-1">
                  <p className="text-[10px] font-headline font-bold text-accent-amber/70 uppercase tracking-[0.2em]">
                    Analysis
                  </p>
                  <div className="bg-bg-base border border-accent-amber/20 p-3 text-xs text-text-secondary leading-relaxed max-h-40 overflow-y-auto whitespace-pre-wrap">
                    {stripLeadingHeading(analysis)}
                  </div>
                </div>
              )}

              {/* Draft content */}
              {draft && (
                <div className="space-y-1">
                  <p className="text-[10px] font-headline font-bold text-accent-green uppercase tracking-[0.2em] border-b border-accent-green/20 pb-1">
                    Generated Draft
                  </p>
                  <div className="bg-bg-base border border-accent-green/20 p-3 text-xs text-text-secondary leading-relaxed max-h-60 overflow-y-auto whitespace-pre-wrap">
                    {stripLeadingHeading(draft)}
                  </div>
                </div>
              )}

              {/* Actions */}
              <div className="flex flex-wrap gap-2 pt-1">
                <GlowButton
                  variant="secondary"
                  className="py-2 text-[10px] px-3"
                  onClick={handleDeepRead}
                  disabled={deepReading || !!deepRead}
                >
                  {deepReading ? "READING..." : deepRead ? "READ COMPLETE" : "DEEP READ"}
                </GlowButton>
                <GlowButton
                  variant="secondary"
                  className="py-2 text-[10px] px-3"
                  onClick={handleAnalyze}
                  disabled={analyzing || !!analysis}
                >
                  {analyzing ? "ANALYZING..." : analysis ? "ANALYZED" : "ANALYZE"}
                </GlowButton>
                <GlowButton
                  variant="primary"
                  className="py-2 text-[10px] px-3"
                  onClick={handleGenerateDraft}
                  disabled={drafting || !!draft}
                >
                  {drafting ? "GENERATING..." : draft ? "DRAFT READY" : "GENERATE DRAFT"}
                </GlowButton>
                <GlowButton
                  variant="secondary"
                  className="py-2 text-[10px] px-3"
                  onClick={handleDismiss}
                  disabled={dismissing}
                >
                  {dismissing ? "..." : "DISMISS"}
                </GlowButton>
              </div>
            </div>
          </m.div>
        )}
      </AnimatePresence>
    </div>
  );
}

/**
 * BlogQueueTab — Blog ideas queue with hover-expandable cards, draft generation, and status filtering.
 */
export function BlogQueueTab() {
  const { data, isLoading } = useBlogQueue();
  const [filter, setFilter] = useState<BlogFilter>("all");

  const filtered = data?.filter((item) => {
    if (filter === "all") return true;
    return item.status === filter;
  });

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between border-b border-outline-variant/30 pb-2">
        <h2 className="font-headline font-bold text-lg tracking-widest text-cyan-fixed uppercase">
          Blog Queue
        </h2>
        <div className="flex bg-bg-surface p-1 border border-outline-variant/30">
          {(["all", "Idea", "Draft", "Review"] as const).map((f) => (
            <button
              key={f}
              onClick={() => setFilter(f)}
              className={`px-3 py-1 text-[10px] font-headline uppercase tracking-wider transition-colors ${
                filter === f
                  ? "bg-accent-cyan text-bg-base"
                  : "text-text-secondary hover:text-accent-cyan"
              }`}
            >
              {f}
            </button>
          ))}
        </div>
      </div>

      <span className="font-mono text-[10px] text-outline">
        {filtered ? `${filtered.length} ITEMS` : "LOADING..."}
      </span>

      {isLoading || !filtered ? (
        <FeedSkeleton count={5} />
      ) : (
        <div className="space-y-3 max-h-[700px] overflow-y-auto p-2 -m-2">
          {filtered.map((item, i) => (
            <BlogCard key={i} item={item} index={i} />
          ))}
          {filtered.length === 0 && (
            <p className="font-mono text-sm text-text-secondary">
              No items match the current filter
            </p>
          )}
        </div>
      )}
    </div>
  );
}

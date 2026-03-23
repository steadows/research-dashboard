"use client";

import { useState, useCallback } from "react";
import { mutate as swrMutate } from "swr";
import { AnimatePresence, m, useReducedMotion } from "framer-motion";
import { Badge } from "@/components/ui/badge";
import { GlowButton } from "@/components/ui/glow-button";
import { apiMutate } from "@/lib/api";
import { usePapers } from "./hooks";
import { FeedSkeleton } from "./Skeleton";
import type { PaperItem } from "./types";

type RelevanceFilter = "all" | "High" | "Medium" | "Low";

/** Returns true if authors field has meaningful content (not "not indexed" placeholders). */
function hasAuthors(authors: string | null): boolean {
  if (!authors) return false;
  return !authors.toLowerCase().includes("not indexed");
}

const RELEVANCE_COLORS: Record<string, string> = {
  High: "text-accent-green",
  Medium: "text-accent-amber",
  Low: "text-accent-red",
  None: "text-outline",
};

const RELEVANCE_BORDER: Record<string, string> = {
  High: "border-accent-green",
  Medium: "border-accent-amber",
  Low: "border-accent-red",
  None: "border-outline-variant",
};

const RELEVANCE_GLOW: Record<string, string> = {
  High: "hover:box-glow-green",
  Medium: "hover:box-glow-amber",
  Low: "hover:box-glow-red",
  None: "",
};

function PaperCard({
  paper,
  index,
}: {
  paper: PaperItem;
  index: number;
}) {
  const reduceMotion = useReducedMotion();
  const [expanded, setExpanded] = useState(false);
  const [wbStatus, setWbStatus] = useState<"idle" | "sending" | "sent">("idle");
  const [dismissing, setDismissing] = useState(false);

  const handleWorkbench = useCallback(async (e: React.MouseEvent) => {
    e.stopPropagation();
    if (wbStatus !== "idle") return;
    setWbStatus("sending");
    try {
      await apiMutate("/workbench", {
        body: {
          item: {
            source_type: "paper",
            name: paper.title,
            category: paper.relevance_level ?? "Uncategorized",
            status: "New",
            source: `JournalClub ${paper.report_date}`,
            notes: paper.synthesis ?? "",
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
  }, [paper, wbStatus]);

  const handleDismiss = useCallback(async (e: React.MouseEvent) => {
    e.stopPropagation();
    if (dismissing) return;
    setDismissing(true);
    try {
      await apiMutate(`/status/paper::${paper.title}`, { body: { status: "dismissed" } });
      await swrMutate("/papers");
    } catch (err) {
      console.error("Dismiss failed:", err);
      setDismissing(false);
    }
  }, [paper.title, dismissing]);

  const level = paper.relevance_level ?? "None";
  const borderColor = RELEVANCE_BORDER[level] ?? RELEVANCE_BORDER.None;
  const hoverGlow = RELEVANCE_GLOW[level] ?? "";

  return (
    <div
      className={`bg-bg-surface border-l-4 ${borderColor} ${hoverGlow} group transition-all duration-200 cursor-pointer`}
      onClick={() => setExpanded((v) => !v)}
    >
      {/* Header — always visible */}
      <div className="p-5 pb-3">
        <div className="flex justify-between items-start gap-3">
          <div className="flex items-center gap-2 min-w-0">
            <span className="font-mono text-[10px] text-accent-cyan/50 shrink-0">
              [{String(index + 1).padStart(2, "0")}]
            </span>
            <h3 className="font-mono font-bold text-sm text-white group-hover:text-accent-cyan transition-colors truncate">
              {paper.title}
            </h3>
          </div>
          <div className="flex items-center gap-2 shrink-0">
            {paper.relevance_level && (
              <span
                className={`text-[9px] font-headline uppercase tracking-wider ${RELEVANCE_COLORS[level]}`}
              >
                {level}
              </span>
            )}
            <span className="font-mono text-[10px] text-outline">
              {paper.report_date}
            </span>
          </div>
        </div>

        {/* Meta line */}
        {(hasAuthors(paper.authors) || paper.year) && (
          <p className="font-mono text-[10px] text-outline mt-1 pl-[42px]">
            {hasAuthors(paper.authors) && <>{paper.authors}</>}
            {hasAuthors(paper.authors) && paper.year && " | "}
            {paper.year && <>Year: {paper.year}</>}
          </p>
        )}
      </div>

      {/* Expandable body */}
      <AnimatePresence>
        {expanded && (
          <m.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: "auto", opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={
              reduceMotion
                ? { duration: 0 }
                : {
                    height: { type: "spring", stiffness: 400, damping: 30 },
                    opacity: { duration: 0.2 },
                  }
            }
            className="overflow-hidden"
          >
            <div className="px-5 pb-5 space-y-4">
              {paper.snippet && (
                <p className="font-mono text-[11px] text-text-secondary italic leading-relaxed border-l-2 border-accent-cyan/20 pl-3">
                  {paper.snippet}
                </p>
              )}

              {paper.synthesis && (
                <div>
                  <p className="text-[10px] font-headline font-bold text-accent-cyan/70 uppercase tracking-[0.2em] mb-1">
                    Synthesis
                  </p>
                  <p className="font-mono text-[11px] text-text-primary leading-relaxed">
                    {paper.synthesis}
                  </p>
                </div>
              )}

              {paper.relevance && (
                <div>
                  <p className="text-[10px] font-headline font-bold text-accent-cyan/70 uppercase tracking-[0.2em] mb-1">
                    Relevance
                  </p>
                  <p className="font-mono text-[11px] text-text-primary leading-relaxed">
                    <span
                      className={`font-bold ${RELEVANCE_COLORS[level]}`}
                    >
                      {level}
                    </span>
                    {" — "}
                    {paper.relevance.replace(/^(High|Medium|Low|None)\s*—?\s*/i, "")}
                  </p>
                </div>
              )}

              {paper.blog_potential && (
                <div>
                  <p className="text-[10px] font-headline font-bold text-accent-cyan/70 uppercase tracking-[0.2em] mb-1">
                    Blog Potential
                  </p>
                  <p className="font-mono text-[11px] text-text-primary leading-relaxed">
                    {paper.blog_potential}
                  </p>
                </div>
              )}

              {paper.project_applications.length > 0 && (
                <div>
                  <p className="text-[10px] font-headline font-bold text-accent-cyan/70 uppercase tracking-[0.2em] mb-1">
                    Project Applications
                  </p>
                  <ul className="space-y-1">
                    {paper.project_applications.map((app, i) => (
                      <li
                        key={i}
                        className="flex items-start gap-2 font-mono text-[11px] text-text-primary leading-relaxed"
                      >
                        <span className="mt-1.5 h-1 w-1 shrink-0 bg-accent-cyan" />
                        {app}
                      </li>
                    ))}
                  </ul>
                </div>
              )}

              {paper.link && paper.link !== "not indexed" && (
                <div onClick={(e) => e.stopPropagation()}>
                  <a
                    href={paper.link}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="font-mono text-[10px] text-accent-cyan hover:underline"
                  >
                    VIEW PAPER →
                  </a>
                </div>
              )}

              {/* Actions */}
              <div className="flex gap-3 pt-2 border-t border-outline-variant/20">
                <GlowButton
                  variant="secondary"
                  className="flex-1 py-2 text-[10px]"
                  onClick={handleWorkbench}
                  disabled={wbStatus !== "idle"}
                >
                  {wbStatus === "sent" ? "SENT TO WORKBENCH" : wbStatus === "sending" ? "SENDING..." : "SEND TO WORKBENCH"}
                </GlowButton>
                <GlowButton
                  variant="secondary"
                  className="py-2 text-[10px] px-4"
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
 * ResearchArchiveTab — JournalClub paper repository with full breakdowns.
 * Shows all papers across all JournalClub reports with relevance filtering and search.
 */
export function ResearchArchiveTab() {
  const { data, isLoading } = usePapers();
  const [filter, setFilter] = useState<RelevanceFilter>("all");
  const [search, setSearch] = useState("");

  const filtered = data?.filter((paper) => {
    if (filter !== "all" && paper.relevance_level !== filter) return false;
    if (!search) return true;
    const q = search.toLowerCase();
    return (
      paper.title.toLowerCase().includes(q) ||
      (paper.synthesis?.toLowerCase().includes(q) ?? false) ||
      (paper.authors?.toLowerCase().includes(q) ?? false) ||
      paper.project_applications.some((a) => a.toLowerCase().includes(q))
    );
  });

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between border-b border-outline-variant/30 pb-2">
        <h2 className="font-headline font-bold text-lg tracking-widest text-cyan-fixed uppercase">
          Research Archive
        </h2>
        <div className="flex bg-bg-surface p-1 border border-outline-variant/30">
          {(["all", "High", "Medium", "Low"] as const).map((f) => (
            <button
              key={f}
              onClick={() => setFilter(f)}
              className={`px-3 py-1 text-[10px] font-headline uppercase tracking-wider transition-colors ${
                filter === f
                  ? "bg-accent-cyan text-bg-base"
                  : "text-text-secondary hover:text-accent-cyan"
              }`}
            >
              {f === "all" ? "ALL" : f}
            </button>
          ))}
        </div>
      </div>

      <input
        type="text"
        placeholder="Search papers..."
        value={search}
        onChange={(e) => setSearch(e.target.value)}
        className="w-full bg-bg-base border border-outline-variant/30 px-3 py-2 font-mono text-xs text-text-primary placeholder:text-outline/40 focus:border-accent-cyan/50 focus:outline-none"
      />

      <span className="font-mono text-[10px] text-outline">
        {filtered ? `${filtered.length} PAPERS` : "LOADING..."}
      </span>

      {isLoading || !filtered ? (
        <FeedSkeleton count={5} />
      ) : (
        <div className="space-y-3 max-h-[700px] overflow-y-auto p-2 -m-2">
          {filtered.map((paper, i) => (
            <PaperCard
              key={`${paper.report_date}-${i}`}
              paper={paper}
              index={i}
            />
          ))}
          {filtered.length === 0 && (
            <p className="font-mono text-sm text-text-secondary">
              No papers match the current filter
            </p>
          )}
        </div>
      )}
    </div>
  );
}

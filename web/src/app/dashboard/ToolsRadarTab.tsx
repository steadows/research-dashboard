"use client";

import { useState, useCallback, useEffect } from "react";
import { mutate as swrMutate } from "swr";
import { AnimatePresence, m, useReducedMotion } from "framer-motion";
import { Badge } from "@/components/ui/badge";
import { GlowButton } from "@/components/ui/glow-button";
import { apiMutate } from "@/lib/api";
import { useTools } from "./hooks";
import { FeedSkeleton } from "./Skeleton";
import type { ToolItem } from "./types";

function ToolCard({ tool, index }: { tool: ToolItem; index: number }) {
  const [hovered, setHovered] = useState(false);
  const [wbStatus, setWbStatus] = useState<"idle" | "sending" | "sent">("idle");
  const [dismissing, setDismissing] = useState(false);
  const [lazySummary, setLazySummary] = useState<string | null>(null);
  const reduceMotion = useReducedMotion();

  // Lazily fetch summary from Haiku if not cached
  useEffect(() => {
    if (tool.summary || lazySummary) return;
    let cancelled = false;
    apiMutate<{ summary: string }>("/tools/summarize", { body: { name: tool.name } })
      .then((res) => { if (!cancelled) setLazySummary(res.summary); })
      .catch((err) => console.error("Tool summary failed:", err));
    return () => { cancelled = true; };
  }, [tool.name, tool.summary, lazySummary]);

  const displaySummary = tool.summary || lazySummary;

  const dotColor =
    tool.status === "offline"
      ? "bg-accent-red"
      : tool.source === "tldr"
        ? "bg-accent-amber shadow-[0_0_5px_#ffbf00]"
        : "bg-accent-green shadow-[0_0_5px_#39ff14]";

  const handleDismiss = useCallback(async (e: React.MouseEvent) => {
    e.stopPropagation();
    if (dismissing) return;
    setDismissing(true);
    try {
      await apiMutate(`/status/tool::${tool.name}`, { body: { status: "dismissed" } });
      await swrMutate("/tools");
    } catch (err) {
      console.error("Dismiss failed:", err);
      setDismissing(false);
    }
  }, [tool.name, dismissing]);

  const handleWorkbench = useCallback(async (e: React.MouseEvent) => {
    e.stopPropagation();
    if (wbStatus !== "idle") return;
    setWbStatus("sending");
    try {
      await apiMutate("/workbench", {
        body: {
          item: {
            source_type: "tool",
            name: tool.name,
            category: tool.category,
            status: tool.status,
            source: tool.source,
            notes: tool.notes,
            tags: tool.tags?.join(", ") ?? "",
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
  }, [tool, wbStatus]);

  return (
    <m.div
      className="bg-bg-surface p-5 border-l-4 border-accent-green group cursor-pointer"
      animate={{
        backgroundColor: hovered ? "rgba(0, 240, 255, 0.06)" : "rgba(17, 24, 39, 1)",
        boxShadow: hovered
          ? "inset 0 0 0 1px rgba(57, 255, 20, 0.3)"
          : "inset 0 0 0 1px rgba(57, 255, 20, 0)",
      }}
      transition={{ duration: 0.15 }}
      onMouseEnter={() => setHovered(true)}
      onMouseLeave={() => setHovered(false)}
    >
      {/* Header row */}
      <div className="flex justify-between items-start mb-2">
        <div className="flex items-center gap-3">
          <m.div
            className={`h-2 w-2 shrink-0 rounded-full ${dotColor}`}
            animate={{ scale: hovered ? 1.5 : 1 }}
            transition={{ type: "spring", stiffness: 500, damping: 20 }}
          />
          <h3 className="font-mono font-bold text-white group-hover:text-accent-cyan transition-colors">
            {tool.name}
          </h3>
        </div>
        <span className="font-mono text-[10px] text-accent-cyan/50">
          [{String(index + 1).padStart(2, "0")}]
        </span>
      </div>

      {tool.category && (
        <Badge variant="tool" className="mr-2 mb-2">{tool.category}</Badge>
      )}

      {tool.tags && tool.tags.length > 0 && (
        <div className="flex flex-wrap gap-1.5 mt-2">
          {tool.tags.map((tag) => (
            <span
              key={tag}
              className="text-[9px] font-mono border border-accent-cyan/40 text-accent-cyan px-2 py-0.5"
            >
              {tag.toUpperCase()}
            </span>
          ))}
        </div>
      )}

      {(displaySummary || tool.notes) && (
        <p className="font-mono text-[11px] text-text-secondary mt-3 leading-relaxed">
          {displaySummary || tool.notes}
        </p>
      )}

      {/* Animated hover-reveal drawer */}
      <AnimatePresence>
        {hovered && (
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
            <div className="mt-4 pt-4 border-t border-outline-variant/20 space-y-4">
              {(tool.source || tool.url) && (
                <m.div
                  initial={{ x: -10 }}
                  animate={{ x: 0 }}
                  transition={{ type: "spring", stiffness: 400, damping: 25, delay: 0.04 }}
                >
                  <p className="text-[10px] font-headline font-bold text-text-secondary uppercase tracking-[0.2em] mb-1">
                    Source
                  </p>
                  {tool.url ? (
                    <a
                      href={tool.url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="inline-flex items-center gap-1.5 font-mono text-[11px] text-accent-cyan hover:underline"
                      onClick={(e) => e.stopPropagation()}
                    >
                      {tool.source || tool.url}
                      <svg className="h-3 w-3 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                        <path strokeLinecap="round" strokeLinejoin="round" d="M13.5 6H5.25A2.25 2.25 0 003 8.25v10.5A2.25 2.25 0 005.25 21h10.5A2.25 2.25 0 0018 18.75V10.5m-4.5-6H21m0 0v7.5m0-7.5l-9 9" />
                      </svg>
                    </a>
                  ) : (
                    <p className="font-mono text-[11px] text-accent-cyan/70">{tool.source}</p>
                  )}
                </m.div>
              )}

              <m.div
                initial={{ opacity: 0, y: 6 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ type: "spring", stiffness: 400, damping: 25, delay: 0.1 }}
                className="flex gap-3"
                onClick={(e) => e.stopPropagation()}
              >
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
              </m.div>
            </div>
          </m.div>
        )}
      </AnimatePresence>
    </m.div>
  );
}

/**
 * ToolsRadarTab — Full tools radar view with category filter and animated hover-reveal cards.
 */
export function ToolsRadarTab() {
  const { data, isLoading } = useTools();
  const [categoryFilter, setCategoryFilter] = useState<string>("all");

  const categories = data
    ? ["all", ...new Set(data.map((t) => t.category).filter(Boolean) as string[])]
    : ["all"];

  const filtered = data?.filter(
    (t) => categoryFilter === "all" || t.category === categoryFilter
  );

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between border-b border-outline-variant/30 pb-2">
        <h2 className="font-headline font-bold text-lg tracking-widest text-cyan-fixed uppercase">
          Tools Radar
        </h2>
        <span className="font-mono text-[10px] text-outline">
          {filtered ? `${filtered.length} TOOLS` : "LOADING..."}
        </span>
      </div>

      {/* Category filter */}
      {categories.length > 1 && (
        <div className="flex flex-wrap gap-2">
          {categories.map((cat) => (
            <button
              key={cat}
              onClick={() => setCategoryFilter(cat)}
              className={`px-3 py-1 text-[10px] font-headline uppercase tracking-wider border transition-colors ${
                categoryFilter === cat
                  ? "bg-accent-cyan text-bg-base border-accent-cyan"
                  : "border-outline-variant/30 text-text-secondary hover:text-accent-cyan hover:border-accent-cyan/50"
              }`}
            >
              {cat}
            </button>
          ))}
        </div>
      )}

      {isLoading || !filtered ? (
        <FeedSkeleton count={5} />
      ) : filtered.length === 0 ? (
        <p className="font-mono text-sm text-text-secondary">
          No tools match the current filter
        </p>
      ) : (
        <>
          {/* Mobile: single column */}
          <div className="space-y-4 max-h-[700px] overflow-y-auto pr-2 md:hidden">
            {filtered.map((tool, i) => (
              <ToolCard key={`${tool.name}-${i}`} tool={tool} index={i} />
            ))}
          </div>
          {/* Desktop: two independent columns (no shared grid rows) */}
          <div className="hidden md:flex gap-4 max-h-[700px] overflow-y-auto pr-2 items-start">
            <div className="flex-1 space-y-4">
              {filtered.filter((_, i) => i % 2 === 0).map((tool, i) => (
                <ToolCard key={`${tool.name}-${i * 2}`} tool={tool} index={i * 2} />
              ))}
            </div>
            <div className="flex-1 space-y-4">
              {filtered.filter((_, i) => i % 2 === 1).map((tool, i) => (
                <ToolCard key={`${tool.name}-${i * 2 + 1}`} tool={tool} index={i * 2 + 1} />
              ))}
            </div>
          </div>
        </>
      )}
    </div>
  );
}

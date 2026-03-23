"use client";

import { useState, useCallback } from "react";
import { mutate as swrMutate } from "swr";
import { AnimatePresence, m, useReducedMotion } from "framer-motion";
import { MetricCard } from "@/components/ui/metric-card";
import { Badge } from "@/components/ui/badge";
import { GlowButton } from "@/components/ui/glow-button";
import { SectionRevealGroup, SectionRevealItem } from "@/components/effects/SectionReveal";
import { apiMutate } from "@/lib/api";
import { useDashboardStats, useHomeSummary, useReports, useTools } from "./hooks";
import { MetricCardsSkeleton, FeedSkeleton, ToolsListSkeleton } from "./Skeleton";
import type { HomeSummary, ReportItem, ToolItem } from "./types";

/** Format number with leading zero for single digits */
function pad(n: number): string {
  return n < 10 ? `0${n}` : String(n);
}

// ─── Sub-components ──────────────────────────────────────────────────────────

function MetricCards() {
  const { data, isLoading } = useDashboardStats();

  if (isLoading || !data) return <MetricCardsSkeleton />;

  return (
    <SectionRevealGroup animation="fadeUp" staggerDelay={0.08} className="grid grid-cols-1 gap-6 sm:grid-cols-2 lg:grid-cols-4">
      <SectionRevealItem>
        <MetricCard
          index="[01]"
          title="Papers"
          value={pad(data.papers)}
        />
      </SectionRevealItem>
      <SectionRevealItem>
        <MetricCard
          index="[02]"
          title="Tools"
          value={pad(data.tools)}
        />
      </SectionRevealItem>
      <SectionRevealItem>
        <MetricCard
          index="[03]"
          title="Blog Queue"
          value={pad(data.blog_queue)}
        />
      </SectionRevealItem>
      <SectionRevealItem>
        <MetricCard
          index="[04]"
          title="Active Projects"
          value={pad(data.active_projects)}
        />
      </SectionRevealItem>
    </SectionRevealGroup>
  );
}

function ResearchFeedCard({
  item,
  expanded,
  onToggle,
}: {
  item: ReportItem;
  expanded: boolean;
  onToggle: () => void;
}) {
  const reduceMotion = useReducedMotion();
  const isJC = item.type === "journalclub";
  const borderColor = isJC ? "border-accent-green" : "border-accent-amber";
  const hoverGlow = isJC ? "hover:box-glow-green" : "hover:box-glow-amber";
  const badgeVariant = isJC ? "journalclub" : "tldr";
  const badgeLabel = isJC ? "JOURNALCLUB" : "TLDR";

  return (
    <div
      onClick={onToggle}
      className={`bg-bg-surface border-l-4 ${borderColor} ${hoverGlow} cursor-pointer group hover:bg-surface-high/50 transition-all duration-200`}
    >
      <div className="p-5 pb-3">
        <div className="flex justify-between items-start mb-1">
          <div className="flex items-center gap-2 pr-3">
            <m.span
              animate={{ rotate: expanded ? 90 : 0 }}
              transition={{ duration: 0.15 }}
              className="text-accent-cyan/60 text-[10px]"
            >
              ▶
            </m.span>
            <h3 className="font-mono font-bold text-white group-hover:text-accent-cyan transition-colors">
              {item.title}
            </h3>
          </div>
          <div className="flex items-center gap-2 shrink-0">
            <span className="font-mono text-[10px] text-outline">{item.date}</span>
            <Badge variant={badgeVariant}>{badgeLabel}</Badge>
          </div>
        </div>
      </div>

      <AnimatePresence initial={false}>
        {expanded && (
          <m.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: "auto", opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={
              reduceMotion
                ? { duration: 0 }
                : { height: { type: "spring", stiffness: 400, damping: 30 }, opacity: { duration: 0.2 } }
            }
            className="overflow-hidden"
          >
            <div className="px-5 pb-5 space-y-3">
              {item.summary && (
                <p className="font-mono text-[11px] text-text-secondary leading-relaxed border-l-2 border-accent-cyan/30 pl-3">
                  {item.summary}
                </p>
              )}
              {item.highlights && item.highlights.length > 0 && (
                <ul className="space-y-2 text-sm text-text-primary">
                  {item.highlights.map((h, i) => (
                    <li key={i} className="flex items-start gap-2">
                      <span className="mt-1.5 h-1 w-1 shrink-0 bg-accent-cyan" />
                      {h}
                    </li>
                  ))}
                </ul>
              )}
            </div>
          </m.div>
        )}
      </AnimatePresence>
    </div>
  );
}

function IntelBriefCard({
  summary,
  expanded,
  onToggle,
}: {
  summary: HomeSummary;
  expanded: boolean;
  onToggle: () => void;
}) {
  const reduceMotion = useReducedMotion();

  return (
    <div
      onClick={onToggle}
      className="bg-bg-surface border-l-4 border-accent-cyan hover:box-glow-cyan cursor-pointer group hover:bg-surface-high/50 transition-all duration-200"
    >
      <div className="p-5 pb-3">
        <div className="flex justify-between items-start mb-1">
          <div className="flex items-center gap-2 pr-3">
            <m.span
              animate={{ rotate: expanded ? 90 : 0 }}
              transition={{ duration: 0.15 }}
              className="text-accent-cyan/60 text-[10px]"
            >
              ▶
            </m.span>
            <h3 className="font-mono font-bold text-white group-hover:text-accent-cyan transition-colors">
              INTEL BRIEF
            </h3>
          </div>
          <Badge variant="default">LATEST</Badge>
        </div>
      </div>

      <AnimatePresence initial={false}>
        {expanded && (
          <m.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: "auto", opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={
              reduceMotion
                ? { duration: 0 }
                : { height: { type: "spring", stiffness: 400, damping: 30 }, opacity: { duration: 0.2 } }
            }
            className="overflow-hidden"
          >
            <div className="px-5 pb-5 grid grid-cols-2 gap-6">
              {/* Top Picks */}
              {summary.top_picks.length > 0 && (
                <div className="space-y-2">
                  <h4 className="font-headline text-[10px] uppercase tracking-widest text-accent-cyan/70">
                    JournalClub Top Picks
                  </h4>
                  <ul className="space-y-1.5">
                    {summary.top_picks.slice(0, 3).map((pick, i) => (
                      <li key={i} className="flex items-start gap-2 text-[11px] font-mono text-text-primary leading-relaxed">
                        <span className="mt-1.5 h-1 w-1 shrink-0 bg-accent-green" />
                        {pick}
                      </li>
                    ))}
                  </ul>
                </div>
              )}

              {/* Blog Ideas */}
              {summary.blog_ideas.length > 0 && (
                <div className="space-y-2">
                  <h4 className="font-headline text-[10px] uppercase tracking-widest text-accent-cyan/70">
                    Blog Ideas
                  </h4>
                  <ul className="space-y-1.5">
                    {summary.blog_ideas.map((idea, i) => (
                      <li key={i} className="flex items-center gap-2 text-[11px] font-mono text-text-primary">
                        <span className="text-white font-bold">{idea.title}</span>
                        <span className="text-[9px] text-outline uppercase">{idea.status}</span>
                      </li>
                    ))}
                  </ul>
                </div>
              )}

              {/* Top Tools */}
              {summary.top_tools.length > 0 && (
                <div className="space-y-2">
                  <h4 className="font-headline text-[10px] uppercase tracking-widest text-accent-cyan/70">
                    Top Tools
                  </h4>
                  <ul className="space-y-1.5">
                    {summary.top_tools.map((tool, i) => (
                      <li key={i} className="flex items-center gap-2 text-[11px] font-mono">
                        <span className="h-1.5 w-1.5 rounded-full bg-accent-amber shadow-[0_0_5px_#ffbf00]" />
                        <span className="text-white">{tool.name}</span>
                        {tool.category && (
                          <span className="text-[9px] text-outline">({tool.category})</span>
                        )}
                      </li>
                    ))}
                  </ul>
                </div>
              )}

              {/* AI Signal */}
              {summary.ai_signal && (
                <div className="space-y-2">
                  <h4 className="font-headline text-[10px] uppercase tracking-widest text-accent-cyan/70">
                    Weekly AI Signal
                  </h4>
                  <p className="text-[11px] font-mono text-text-secondary leading-relaxed">
                    {summary.ai_signal}
                  </p>
                  {summary.ai_signal_source && (
                    <p className="text-[9px] font-mono text-accent-cyan/40">
                      From {summary.ai_signal_source}
                    </p>
                  )}
                </div>
              )}
            </div>
          </m.div>
        )}
      </AnimatePresence>
    </div>
  );
}

function ResearchFeed() {
  const { data, isLoading } = useReports();
  const { data: summary, isLoading: summaryLoading } = useHomeSummary();
  // -1 = intel brief, 0+ = report cards, -2 = none expanded.
  // Intel brief expanded by default.
  const [expandedIndex, setExpandedIndex] = useState(-1);

  const handleToggle = useCallback((index: number) => {
    setExpandedIndex((prev) => (prev === index ? -2 : index));
  }, []);

  return (
    <section className="lg:col-span-2 space-y-6">
      <div className="flex items-center justify-between border-b border-outline-variant/30 pb-2">
        <h2 className="font-headline font-bold text-lg tracking-widest text-cyan-fixed uppercase">
          Research Feed
        </h2>
        <span className="font-mono text-[10px] text-outline">
          LATEST UPDATES // PAGE 01
        </span>
      </div>

      {(isLoading && !data) || summaryLoading ? (
        <FeedSkeleton count={3} />
      ) : (
        <div className="space-y-4 max-h-[700px] overflow-y-auto p-2 -m-2">
          {summary && (
            <IntelBriefCard
              summary={summary}
              expanded={expandedIndex === -1}
              onToggle={() => handleToggle(-1)}
            />
          )}
          {data?.slice(0, 10).map((item, i) => (
            <ResearchFeedCard
              key={i}
              item={item}
              expanded={expandedIndex === i}
              onToggle={() => handleToggle(i)}
            />
          ))}
          {(!data || data.length === 0) && !summary && (
            <p className="font-mono text-sm text-text-secondary">
              No reports available
            </p>
          )}
        </div>
      )}
    </section>
  );
}

function ToolRadarItem({ tool }: { tool: ToolItem }) {
  const [hovered, setHovered] = useState(false);
  const [wbStatus, setWbStatus] = useState<"idle" | "sending" | "sent">("idle");
  const reduceMotion = useReducedMotion();

  const dotColor =
    tool.status === "offline"
      ? "bg-accent-red"
      : tool.source === "tldr"
        ? "bg-accent-amber shadow-[0_0_5px_#ffbf00]"
        : "bg-accent-green shadow-[0_0_5px_#39ff14]";

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
      className="group cursor-pointer p-2"
      animate={{
        backgroundColor: hovered ? "rgba(0, 240, 255, 0.08)" : "rgba(0, 240, 255, 0)",
      }}
      transition={{ duration: 0.15 }}
      onMouseEnter={() => setHovered(true)}
      onMouseLeave={() => setHovered(false)}
    >
      {/* Collapsed row */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <m.div
            className={`h-1.5 w-1.5 rounded-full ${dotColor}`}
            animate={{ scale: hovered ? 1.6 : 1 }}
            transition={{ type: "spring", stiffness: 500, damping: 20 }}
          />
          <span className="font-mono text-sm text-white">
            {tool.name.toUpperCase().replace(/\s+/g, "_")}
          </span>
        </div>
        {tool.category && (
          <m.span
            className="text-[9px] font-headline border px-1.5"
            animate={{
              color: hovered ? "#00F0FF" : "#6B7280",
              borderColor: hovered ? "#00F0FF" : "#374151",
            }}
            transition={{ duration: 0.15 }}
          >
            {tool.category.toUpperCase()}
          </m.span>
        )}
      </div>

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
            <div className="pt-2 space-y-2">
              {(tool.summary || tool.notes) && (
                <m.p
                  initial={{ x: -8 }}
                  animate={{ x: 0 }}
                  transition={{ type: "spring", stiffness: 400, damping: 25, delay: 0.05 }}
                  className="font-mono text-[10px] text-text-secondary leading-relaxed pl-[18px]"
                >
                  {tool.summary || tool.notes}
                </m.p>
              )}
              {tool.source && (
                <m.p
                  initial={{ x: -8 }}
                  animate={{ x: 0 }}
                  transition={{ type: "spring", stiffness: 400, damping: 25, delay: 0.08 }}
                  className="font-mono text-[9px] text-accent-cyan/50 pl-[18px]"
                >
                  via {tool.source}
                </m.p>
              )}
              <m.div
                initial={{ opacity: 0, y: 4 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ type: "spring", stiffness: 400, damping: 25, delay: 0.1 }}
                className="pl-[18px] pt-1"
              >
                <GlowButton
                  variant="secondary"
                  className="py-1 px-3 text-[9px]"
                  onClick={handleWorkbench}
                  disabled={wbStatus !== "idle"}
                >
                  {wbStatus === "sent" ? "SENT" : wbStatus === "sending" ? "..." : "DEEP DIVE"}
                </GlowButton>
              </m.div>
            </div>
          </m.div>
        )}
      </AnimatePresence>
    </m.div>
  );
}

function ToolsRadarSidebar() {
  const { data, isLoading } = useTools();

  return (
    <section className="space-y-6">
      <div className="flex items-center justify-between border-b border-outline-variant/30 pb-2">
        <h2 className="font-headline font-bold text-lg tracking-widest text-cyan-fixed uppercase">
          Tools Radar
        </h2>
        <svg
          className="h-4 w-4 text-cyan-fixed animate-spin"
          style={{ animationDuration: "4s" }}
          fill="none"
          viewBox="0 0 24 24"
          stroke="currentColor"
          strokeWidth={1.5}
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            d="M16.023 9.348h4.992v-.001M2.985 19.644v-4.992m0 0h4.992m-4.993 0l3.181 3.183a8.25 8.25 0 0013.803-3.7M4.031 9.865a8.25 8.25 0 0113.803-3.7l3.181 3.182M2.985 19.644l3.18-3.182"
          />
        </svg>
      </div>

      <div className="bg-bg-base border border-outline-variant/20 p-4 space-y-1">
        {isLoading || !data ? (
          <ToolsListSkeleton count={5} />
        ) : (
          <>
            {data.slice(0, 8).map((tool, i) => (
              <ToolRadarItem key={i} tool={tool} />
            ))}
            {data.length === 0 && (
              <p className="font-mono text-sm text-text-secondary p-2">
                No tools tracked
              </p>
            )}
          </>
        )}
      </div>

    </section>
  );
}


// ─── Main Component ──────────────────────────────────────────────────────────

/**
 * HomeTab — Default dashboard view matching the Stitch dashboard.html design.
 * Shows metric cards, research feed, tools radar sidebar, and weekly signal.
 */
export function HomeTab() {
  return (
    <div className="space-y-8">
      <MetricCards />

      <div className="grid grid-cols-1 gap-8 lg:grid-cols-3">
        <ResearchFeed />
        <ToolsRadarSidebar />
      </div>

    </div>
  );
}

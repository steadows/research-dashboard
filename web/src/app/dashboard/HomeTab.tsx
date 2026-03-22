"use client";

import { MetricCard } from "@/components/ui/metric-card";
import { Badge } from "@/components/ui/badge";
import { SectionRevealGroup, SectionRevealItem } from "@/components/effects/SectionReveal";
import { useDashboardStats, useReports, useTools } from "./hooks";
import { MetricCardsSkeleton, FeedSkeleton, ToolsListSkeleton } from "./Skeleton";
import type { ReportItem, ToolItem } from "./types";

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
          delta={"+2.4% \u0394"}
          deltaColor="green"
          meta={"40.7128\u00b0 N"}
        />
      </SectionRevealItem>
      <SectionRevealItem>
        <MetricCard
          index="[02]"
          title="Tools"
          value={pad(data.tools)}
          delta="SYNCED"
          deltaColor="amber"
          meta={"74.0060\u00b0 W"}
        />
      </SectionRevealItem>
      <SectionRevealItem>
        <MetricCard
          index="[03]"
          title="Blog Queue"
          value={pad(data.blog_queue)}
          meta="EST. 14:00"
        />
      </SectionRevealItem>
      <SectionRevealItem>
        <MetricCard
          index="[04]"
          title="Active Projects"
          value={pad(data.active_projects)}
          deltaColor="green"
          meta="AUTH: LVL 5"
        />
      </SectionRevealItem>
    </SectionRevealGroup>
  );
}

function ResearchFeedCard({ item }: { item: ReportItem }) {
  const borderColor =
    item.type === "journalclub" ? "border-accent-green" : "border-accent-amber";
  const badgeVariant = item.type === "journalclub" ? "journalclub" : "tldr";
  const badgeLabel = item.type === "journalclub" ? "JOURNALCLUB" : "TLDR";

  return (
    <div
      className={`bg-bg-surface p-5 border-l-4 ${borderColor} group hover:bg-surface-high/50 transition-colors`}
    >
      <div className="flex justify-between items-start mb-3">
        <h3 className="font-mono font-bold text-white group-hover:text-accent-cyan transition-colors pr-3">
          {item.title}
        </h3>
        <Badge variant={badgeVariant}>{badgeLabel}</Badge>
      </div>
      <p className="font-mono text-[11px] text-outline mb-3 italic">
        Published: {item.date}
      </p>
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
  );
}

function ResearchFeed() {
  const { data, isLoading } = useReports();

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

      {isLoading || !data ? (
        <FeedSkeleton count={3} />
      ) : (
        <div className="space-y-4 max-h-[600px] overflow-y-auto pr-2">
          {data.slice(0, 10).map((item, i) => (
            <ResearchFeedCard key={i} item={item} />
          ))}
          {data.length === 0 && (
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
  const dotColor =
    tool.status === "offline"
      ? "bg-accent-red"
      : tool.source === "tldr"
        ? "bg-accent-amber shadow-[0_0_5px_#ffbf00]"
        : "bg-accent-green shadow-[0_0_5px_#39ff14]";

  return (
    <div className="flex items-center justify-between group cursor-pointer hover:bg-accent-cyan/5 p-2 transition-colors">
      <div className="flex items-center gap-3">
        <div className={`h-1.5 w-1.5 rounded-full ${dotColor}`} />
        <span className="font-mono text-sm text-white">
          {tool.name.toUpperCase().replace(/\s+/g, "_")}
        </span>
      </div>
      {tool.category && (
        <span className="text-[9px] font-headline border border-outline-variant px-1.5 text-outline group-hover:text-accent-cyan group-hover:border-accent-cyan">
          {tool.category.toUpperCase()}
        </span>
      )}
    </div>
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

      {/* Radar graphic placeholder */}
      <div className="aspect-square relative flex items-center justify-center border border-accent-cyan/10">
        <div className="absolute inset-0 flex items-center justify-center">
          <div className="h-full w-full scale-90 border border-accent-cyan/20 rounded-full" />
          <div className="absolute h-full w-full scale-75 border border-accent-cyan/10 rounded-full" />
          <div className="absolute h-full w-full scale-50 border border-accent-cyan/5 rounded-full" />
        </div>
        <div className="absolute left-1/2 top-0 h-full w-[1px] -translate-x-1/2 bg-accent-cyan/20" />
        <div className="absolute top-1/2 left-0 h-[1px] w-full -translate-y-1/2 bg-accent-cyan/20" />
        <span className="font-mono text-[10px] text-accent-cyan/60 z-10 bg-bg-base px-2">
          RADAR ACTIVE
        </span>
      </div>
    </section>
  );
}

function WeeklySignal() {
  return (
    <section className="space-y-4">
      <div className="flex items-center justify-between">
        <h2 className="font-headline font-bold text-lg tracking-widest text-cyan-fixed uppercase">
          Weekly Signal
        </h2>
        <div className="flex gap-4">
          <div className="flex items-center gap-2">
            <div className="h-1 w-3 bg-accent-cyan" />
            <span className="font-mono text-[10px] text-outline">
              INTEL_DENSITY
            </span>
          </div>
          <div className="flex items-center gap-2">
            <div className="h-1 w-3 bg-outline-variant" />
            <span className="font-mono text-[10px] text-outline">BASELINE</span>
          </div>
        </div>
      </div>

      <div className="h-48 bg-bg-surface border border-outline-variant/20 relative overflow-hidden p-4">
        {/* Grid lines */}
        <div className="absolute inset-0 grid grid-cols-7 grid-rows-4 pointer-events-none opacity-10">
          {Array.from({ length: 28 }, (_, i) => (
            <div
              key={i}
              className="border-r border-b border-accent-cyan"
            />
          ))}
        </div>

        {/* SVG chart placeholder */}
        <svg
          className="absolute inset-0 h-full w-full p-4 overflow-visible"
          preserveAspectRatio="none"
        >
          <path
            className="drop-glow-cyan"
            d="M0 120 L80 110 L160 140 L240 80 L320 100 L400 30 L480 90 L560 70 L640 110 L720 40 L800 60"
            fill="none"
            stroke="#00F0FF"
            strokeWidth="2"
          />
          <circle cx="400" cy="30" fill="#00F0FF" r="3" />
          <circle cx="720" cy="40" fill="#00F0FF" r="3" />
        </svg>

        {/* Day labels */}
        <div className="absolute bottom-2 left-4 right-4 flex justify-between font-mono text-[9px] text-outline/60">
          <span>MON</span>
          <span>TUE</span>
          <span>WED</span>
          <span>THU</span>
          <span>FRI</span>
          <span>SAT</span>
          <span>SUN</span>
        </div>
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

      <WeeklySignal />
    </div>
  );
}

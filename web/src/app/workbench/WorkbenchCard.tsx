"use client";

import { LazyMotion, domAnimation, m } from "framer-motion";
import { cn } from "@/lib/utils";
import { Badge } from "@/components/ui/badge";
import { GlowButton } from "@/components/ui/glow-button";
import type { WorkbenchEntry, SourceType } from "./types";

interface WorkbenchCardProps {
  entry: WorkbenchEntry;
  onStartResearch?: (key: string) => void;
  onViewLog?: (key: string) => void;
  onViewReport?: (key: string) => void;
}

const sourceBadgeVariant: Record<SourceType, "tool" | "method" | "instagram"> =
  {
    tool: "tool",
    method: "method",
    instagram: "instagram",
  };

/**
 * WorkbenchCard — Individual item card in the kanban pipeline.
 * Renders differently based on status: queued, researching, completed.
 * Uses Framer Motion layoutId for smooth column transitions.
 */
export function WorkbenchCard({
  entry,
  onStartResearch,
  onViewLog,
  onViewReport,
}: WorkbenchCardProps) {
  return (
    <LazyMotion features={domAnimation}>
      <m.article
        layoutId={entry.key}
        layout
        transition={{ type: "spring", stiffness: 300, damping: 30 }}
        className={cn(
          "relative p-5 transition-all duration-100",
          entry.status === "queued" && [
            "bg-bg-surface border border-transparent",
            "hover:border-accent-cyan/30",
          ],
          entry.status === "researching" && [
            "bg-surface-high border border-accent-cyan/40",
            "box-glow-cyan",
          ],
          entry.status === "completed" && [
            "bg-bg-surface/50 border border-white/5",
            "opacity-80 hover:opacity-100",
          ]
        )}
      >
        {entry.status === "queued" && (
          <QueuedContent
            entry={entry}
            onStartResearch={onStartResearch}
          />
        )}
        {entry.status === "researching" && (
          <ResearchingContent entry={entry} onViewLog={onViewLog} />
        )}
        {entry.status === "completed" && (
          <CompletedContent entry={entry} onViewReport={onViewReport} />
        )}
      </m.article>
    </LazyMotion>
  );
}

function QueuedContent({
  entry,
  onStartResearch,
}: {
  entry: WorkbenchEntry;
  onStartResearch?: (key: string) => void;
}) {
  return (
    <>
      <div className="mb-3 flex items-start justify-between">
        <Badge variant={sourceBadgeVariant[entry.source_type]}>
          {entry.source_type}
        </Badge>
      </div>
      <h3 className="mb-2 font-heading text-base font-bold uppercase leading-tight text-white">
        {entry.name}
      </h3>
      {entry.notes && (
        <p className="mb-5 text-xs leading-relaxed text-text-secondary/60">
          {entry.notes}
        </p>
      )}
      <GlowButton
        variant="secondary"
        className="w-full py-2 text-xs tracking-widest"
        onClick={() => onStartResearch?.(entry.key)}
      >
        START RESEARCH
      </GlowButton>
    </>
  );
}

function ResearchingContent({
  entry,
  onViewLog,
}: {
  entry: WorkbenchEntry;
  onViewLog?: (key: string) => void;
}) {
  return (
    <>
      <div className="mb-3 flex items-start justify-between">
        <div className="flex items-center gap-2">
          <div className="h-1.5 w-1.5 animate-ping rounded-full bg-accent-cyan" />
          <span className="text-[10px] font-bold uppercase tracking-widest text-accent-cyan">
            ACTIVE_SCAN
          </span>
        </div>
      </div>
      <h3 className="mb-2 font-heading text-base font-bold uppercase leading-tight text-white">
        {entry.name}
      </h3>
      {entry.notes && (
        <div className="mb-4 border-l-2 border-accent-cyan/50 bg-black/40 p-3">
          <div className="font-mono text-[9px] leading-tight text-accent-cyan/80">
            {entry.notes}
          </div>
        </div>
      )}
      <GlowButton
        variant="primary"
        className="w-full py-2 text-xs tracking-widest"
        onClick={() => onViewLog?.(entry.key)}
      >
        VIEW LOG
      </GlowButton>
    </>
  );
}

function CompletedContent({
  entry,
  onViewReport,
}: {
  entry: WorkbenchEntry;
  onViewReport?: (key: string) => void;
}) {
  return (
    <>
      <div className="mb-3 flex items-start justify-between">
        {entry.verdict && (
          <VerdictBadge verdict={entry.verdict} />
        )}
      </div>
      <h3 className="mb-2 font-heading text-base font-bold uppercase leading-tight text-white">
        {entry.name}
      </h3>
      {entry.notes && (
        <p className="mb-5 text-[11px] leading-relaxed text-text-secondary/50">
          {entry.notes}
        </p>
      )}
      <div className="flex flex-col gap-2">
        <GlowButton
          variant="primary"
          className="w-full py-1.5 text-[10px] tracking-widest"
          onClick={() => onViewReport?.(entry.key)}
        >
          VIEW REPORT
        </GlowButton>
        <div className="grid grid-cols-2 gap-2">
          <button className="py-1.5 bg-accent-amber text-bg-base font-heading text-[10px] font-bold uppercase">
            SANDBOX
          </button>
          <button className="py-1.5 border border-outline-variant text-text-secondary/60 font-heading text-[10px] font-bold uppercase hover:text-white transition-colors">
            OBSIDIAN
          </button>
        </div>
      </div>
    </>
  );
}

function VerdictBadge({ verdict }: { verdict: "programmatic" | "manual" }) {
  return (
    <span
      className={cn(
        "px-2 py-0.5 text-[10px] font-bold uppercase tracking-widest border",
        verdict === "programmatic" && [
          "bg-accent-green/10 text-accent-green border-accent-green/30",
        ],
        verdict === "manual" && [
          "bg-accent-amber/10 text-accent-amber border-accent-amber/30",
        ]
      )}
    >
      {verdict}
    </span>
  );
}

"use client";

import { useState, useCallback } from "react";
import {
  m,
  AnimatePresence,
  useReducedMotion,
} from "framer-motion";
import { cn } from "@/lib/utils";
import { Badge } from "@/components/ui/badge";
import { GlowButton } from "@/components/ui/glow-button";
import type { WorkbenchEntry, SourceType } from "./types";

interface WorkbenchCardProps {
  entry: WorkbenchEntry;
  onStartResearch?: (key: string) => void;
  onViewLog?: (key: string) => void;
  onViewReport?: (key: string) => void;
  onPublishVault?: (key: string) => void;
  onRemove?: (key: string) => void;
}

const sourceBadgeVariant: Record<SourceType, "tool" | "method" | "instagram"> =
  {
    tool: "tool",
    method: "method",
    instagram: "instagram",
  };

const statusColors: Record<string, string> = {
  queued: "text-accent-cyan",
  researching: "text-accent-amber",
  completed: "text-accent-green",
};

/**
 * WorkbenchCard — Individual item card in the kanban pipeline.
 * Click to expand and reveal rich metadata, summary, and action buttons.
 * Uses Framer Motion for smooth animated expansion.
 */
export function WorkbenchCard({
  entry,
  onStartResearch,
  onViewLog,
  onViewReport,
  onPublishVault,
  onRemove,
}: WorkbenchCardProps) {
  const [expanded, setExpanded] = useState(false);
  const reduceMotion = useReducedMotion();

  const toggleExpand = useCallback(() => {
    setExpanded((prev) => !prev);
  }, []);

  const borderColor =
    entry.source_type === "method"
      ? "border-purple"
      : entry.source_type === "instagram"
        ? "border-indigo"
        : "border-accent-green";

  return (
    <m.article
        layoutId={entry.key}
        layout
        transition={{ type: "spring", stiffness: 300, damping: 30 }}
        className={cn(
          "relative transition-all duration-100 cursor-pointer border-l-4",
          borderColor,
          entry.status === "queued" && [
            "bg-bg-surface",
            "hover:bg-surface-high/30",
          ],
          entry.status === "researching" && [
            "bg-surface-high border-l-accent-cyan",
            "box-glow-cyan",
          ],
          entry.status === "completed" && [
            "bg-bg-surface/50",
            "opacity-80 hover:opacity-100",
          ],
          expanded && "ring-1 ring-accent-cyan/30"
        )}
        onClick={toggleExpand}
      >
        {/* ─── Compact header (always visible) ─── */}
        <div className="p-5">
          <div className="flex items-start justify-between mb-2">
            <div className="flex items-center gap-2 flex-wrap">
              <Badge variant={sourceBadgeVariant[entry.source_type]}>
                {entry.source_type}
              </Badge>
              {entry.category && (
                <span className="text-[9px] font-mono border border-outline-variant/40 text-text-secondary px-2 py-0.5">
                  {entry.category.toUpperCase()}
                </span>
              )}
              {entry.status === "researching" && (
                <div className="flex items-center gap-1.5" role="status" aria-label="Research in progress">
                  <div className="h-1.5 w-1.5 animate-ping rounded-full bg-accent-cyan" aria-hidden="true" />
                  <span className="text-[9px] font-bold uppercase tracking-widest text-accent-cyan">
                    ACTIVE_SCAN
                  </span>
                </div>
              )}
              {entry.verdict && <VerdictBadge verdict={entry.verdict} />}
            </div>
            <span
              className={cn(
                "text-[9px] font-mono uppercase tracking-widest",
                statusColors[entry.status] ?? "text-text-secondary"
              )}
            >
              {entry.status}
            </span>
          </div>

          <h3 className="font-heading text-base font-bold uppercase leading-tight text-white">
            {entry.name}
          </h3>

          {/* Brief preview — always visible */}
          {entry.notes && !expanded && (
            <p className="mt-2 text-xs leading-relaxed text-text-secondary/70 line-clamp-2">
              {entry.notes}
            </p>
          )}

          {entry.added_at && !expanded && (
            <p className="mt-2 text-[9px] font-mono text-text-muted">
              ADDED: {entry.added_at}
            </p>
          )}
        </div>

        {/* ─── Animated click-reveal drawer ─── */}
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
                      height: {
                        type: "spring",
                        stiffness: 500,
                        damping: 30,
                      },
                      opacity: { duration: 0.2 },
                    }
              }
              className="overflow-hidden"
            >
              <div className="px-5 pb-5 space-y-4 border-t border-outline-variant/20 pt-4">
                {/* ─── Rich metadata ─── */}
                <ExpandedMetadata entry={entry} />

                {/* ─── Summary / Description ─── */}
                <ExpandedSummary entry={entry} />

                {/* ─── Tags ─── */}
                {entry.tags && (
                  <m.div
                    initial={{ x: -10 }}
                    animate={{ x: 0 }}
                    transition={{
                      type: "spring",
                      stiffness: 400,
                      damping: 25,
                      delay: 0.06,
                    }}
                    className="flex flex-wrap gap-1.5"
                  >
                    {(typeof entry.tags === "string"
                      ? entry.tags.split(",").map((t) => t.trim())
                      : []
                    )
                      .filter(Boolean)
                      .map((tag) => (
                        <span
                          key={tag}
                          className="text-[9px] font-mono border border-accent-cyan/40 text-accent-cyan px-2 py-0.5"
                        >
                          {tag.toUpperCase()}
                        </span>
                      ))}
                  </m.div>
                )}

                {/* ─── Action buttons ─── */}
                <m.div
                  initial={{ opacity: 0, y: 6 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{
                    type: "spring",
                    stiffness: 400,
                    damping: 25,
                    delay: 0.1,
                  }}
                  className="space-y-2"
                  onClick={(e) => e.stopPropagation()}
                >
                  <StatusActions
                    entry={entry}
                    onStartResearch={onStartResearch}
                    onViewLog={onViewLog}
                    onViewReport={onViewReport}
                    onPublishVault={onPublishVault}
                  />
                  {onRemove && (
                    <button
                      className="w-full py-1.5 border border-accent-red/30 text-accent-red/60 font-heading text-[10px] font-bold uppercase tracking-widest hover:bg-accent-red/10 hover:text-accent-red transition-colors"
                      onClick={() => onRemove(entry.key)}
                    >
                      REMOVE FROM WORKBENCH
                    </button>
                  )}
                </m.div>
              </div>
            </m.div>
          )}
        </AnimatePresence>
      </m.article>
  );
}

/** Metadata rows shown in the expanded drawer */
function ExpandedMetadata({ entry }: { entry: WorkbenchEntry }) {
  const rows: { label: string; value: string }[] = [];

  if (entry.source) rows.push({ label: "Source", value: entry.source });
  if (entry.added_at) rows.push({ label: "Added", value: entry.added_at });
  if (entry.url) rows.push({ label: "URL", value: entry.url });
  if (entry.account) rows.push({ label: "Account", value: `@${entry.account}` });
  if (entry.paper_url) rows.push({ label: "Paper", value: entry.paper_url });

  if (rows.length === 0) return null;

  return (
    <div className="space-y-2">
      {rows.map(({ label, value }, i) => (
        <m.div
          key={label}
          initial={{ x: -10 }}
          animate={{ x: 0 }}
          transition={{
            type: "spring",
            stiffness: 400,
            damping: 25,
            delay: 0.02 * i,
          }}
        >
          <p className="text-[10px] font-headline font-bold text-text-secondary uppercase tracking-[0.2em] mb-0.5">
            {label}
          </p>
          {label === "URL" || label === "Paper" ? (
            <a
              href={value}
              target="_blank"
              rel="noopener noreferrer"
              className="font-mono text-[11px] text-accent-cyan hover:underline break-all"
            >
              {value}
            </a>
          ) : (
            <p className="font-mono text-[11px] text-accent-cyan/70">
              {value}
            </p>
          )}
        </m.div>
      ))}
    </div>
  );
}

/** Summary content based on source type */
function ExpandedSummary({ entry }: { entry: WorkbenchEntry }) {
  // Method: show description / "why it matters"
  if (entry.source_type === "method" && entry.description) {
    return (
      <div className="border-l-2 border-purple/50 bg-black/40 p-3">
        <p className="text-[10px] font-headline font-bold text-text-secondary uppercase tracking-[0.2em] mb-1">
          Why It Matters
        </p>
        <p className="font-mono text-[11px] leading-relaxed text-text-secondary">
          {entry.description}
        </p>
      </div>
    );
  }

  // Instagram: show key points + keywords
  if (entry.source_type === "instagram") {
    return (
      <div className="space-y-3">
        {entry.key_points && entry.key_points.length > 0 && (
          <div className="border-l-2 border-indigo/50 bg-black/40 p-3">
            <p className="text-[10px] font-headline font-bold text-text-secondary uppercase tracking-[0.2em] mb-2">
              Key Points
            </p>
            <ul className="space-y-1">
              {entry.key_points.map((point, i) => (
                <li
                  key={i}
                  className="font-mono text-[11px] text-text-secondary leading-relaxed"
                >
                  <span className="text-accent-cyan mr-2">•</span>
                  {point}
                </li>
              ))}
            </ul>
          </div>
        )}
        {entry.keywords && entry.keywords.length > 0 && (
          <div className="flex flex-wrap gap-1.5">
            {entry.keywords.map((kw) => (
              <span
                key={kw}
                className="text-[9px] font-mono bg-surface-high text-text-secondary px-2 py-0.5"
              >
                {kw}
              </span>
            ))}
          </div>
        )}
        {!entry.key_points?.length && entry.caption && (
          <div className="border-l-2 border-indigo/50 bg-black/40 p-3">
            <p className="font-mono text-[11px] text-text-secondary leading-relaxed italic">
              {entry.caption.slice(0, 300)}
              {entry.caption.length > 300 ? "…" : ""}
            </p>
          </div>
        )}
      </div>
    );
  }

  // Tool: show notes in a styled block
  if (entry.notes) {
    return (
      <div className="border-l-2 border-accent-green/50 bg-black/40 p-3">
        <p className="text-[10px] font-headline font-bold text-text-secondary uppercase tracking-[0.2em] mb-1">
          Notes
        </p>
        <p className="font-mono text-[11px] leading-relaxed text-text-secondary">
          {entry.notes}
        </p>
      </div>
    );
  }

  return null;
}

/** Status-specific action buttons */
function StatusActions({
  entry,
  onStartResearch,
  onViewLog,
  onViewReport,
  onPublishVault,
}: {
  entry: WorkbenchEntry;
  onStartResearch?: (key: string) => void;
  onViewLog?: (key: string) => void;
  onViewReport?: (key: string) => void;
  onPublishVault?: (key: string) => void;
}) {
  if (entry.status === "queued") {
    return (
      <GlowButton
        variant="secondary"
        className="w-full py-2 text-xs tracking-widest"
        onClick={() => onStartResearch?.(entry.key)}
      >
        START RESEARCH
      </GlowButton>
    );
  }

  if (entry.status === "researching") {
    return (
      <GlowButton
        variant="primary"
        className="w-full py-2 text-xs tracking-widest"
        onClick={() => onViewLog?.(entry.key)}
      >
        VIEW LOG
      </GlowButton>
    );
  }

  if (entry.status === "completed") {
    return (
      <div className="space-y-2">
        <GlowButton
          variant="primary"
          className="w-full py-1.5 text-[10px] tracking-widest"
          onClick={() => onViewReport?.(entry.key)}
        >
          VIEW REPORT
        </GlowButton>
        <div className="grid grid-cols-2 gap-2">
          <button
            className="py-1.5 bg-accent-amber text-bg-base font-heading text-[10px] font-bold uppercase"
            aria-label={`Open ${entry.name} in sandbox`}
          >
            SANDBOX
          </button>
          <button
            className={`py-1.5 border font-heading text-[10px] font-bold uppercase transition-colors ${
              entry.vault_note
                ? "border-accent-green text-accent-green hover:text-white"
                : "border-outline-variant text-text-secondary/70 hover:text-white"
            }`}
            aria-label={`Open ${entry.name} in Obsidian`}
            onClick={() => onPublishVault?.(entry.key)}
          >
            {entry.vault_note ? "OPEN IN VAULT" : "OBSIDIAN"}
          </button>
        </div>
      </div>
    );
  }

  return null;
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

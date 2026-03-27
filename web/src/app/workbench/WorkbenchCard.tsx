"use client";

import { useState, useCallback, useEffect } from "react";
import {
  m,
  AnimatePresence,
  useReducedMotion,
} from "framer-motion";
import { cn } from "@/lib/utils";
import { Badge } from "@/components/ui/badge";
import { GlowButton } from "@/components/ui/glow-button";
import ReactMarkdown from "react-markdown";
import type { WorkbenchEntry, SourceType } from "./types";

interface WorkbenchCardProps {
  entry: WorkbenchEntry;
  /** Card is rendered full-width in focus mode */
  focused?: boolean;
  onStartResearch?: (key: string) => void;
  onStartSandbox?: (key: string) => void;
  onViewLog?: (key: string) => void;
  onViewReport?: (key: string) => void;
  onPublishVault?: (key: string) => void;
  onRemove?: (key: string) => void;
  onFocus?: (key: string) => void;
  onCollapse?: () => void;
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
  researched: "text-accent-green",
  sandbox_creating: "text-accent-amber",
  sandbox_ready: "text-accent-green",
  experiment_running: "text-accent-amber",
  experiment_done: "text-accent-green",
  manual: "text-accent-amber",
  failed: "text-accent-red",
  completed: "text-accent-green",
};

/**
 * WorkbenchCard — Individual item card in the kanban pipeline.
 * Click to expand and reveal rich metadata, summary, and action buttons.
 * Uses Framer Motion for smooth animated expansion.
 */
export function WorkbenchCard({
  entry,
  focused = false,
  onStartResearch,
  onStartSandbox,
  onViewLog,
  onViewReport,
  onPublishVault,
  onRemove,
  onFocus,
  onCollapse,
}: WorkbenchCardProps) {
  const [expanded, setExpanded] = useState(focused);
  const reduceMotion = useReducedMotion();

  // Auto-expand when entering focus mode
  useEffect(() => {
    if (focused) setExpanded(true);
  }, [focused]);

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
          entry.status === "sandbox_creating" && [
            "bg-surface-high border-l-accent-amber",
            "box-glow-amber",
          ],
          entry.status === "sandbox_ready" && [
            "bg-bg-surface border-l-accent-green",
          ],
          entry.status === "experiment_running" && [
            "bg-surface-high border-l-accent-amber",
            "box-glow-amber",
          ],
          entry.status === "experiment_done" && [
            "bg-bg-surface border-l-accent-green",
          ],
          (entry.status === "researched" || entry.status === "completed") && [
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
          {(entry.description || entry.notes) && !expanded && (
            <p className="mt-2 text-xs leading-relaxed text-text-secondary/70 line-clamp-2">
              {entry.description || entry.notes}
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
                  {/* Focus/collapse toggle for completed-column items */}
                  {(onFocus || onCollapse) && (
                    <button
                      className={cn(
                        "w-full py-1.5 border font-heading text-[10px] font-bold uppercase tracking-widest transition-colors",
                        focused
                          ? "border-accent-cyan/50 text-accent-cyan hover:bg-accent-cyan/10"
                          : "border-outline-variant/50 text-text-secondary hover:text-white hover:border-accent-cyan/30"
                      )}
                      onClick={() => focused ? onCollapse?.() : onFocus?.(entry.key)}
                    >
                      {focused ? "COLLAPSE" : "EXPAND FULL WIDTH"}
                    </button>
                  )}
                  <StatusActions
                    entry={entry}
                    onStartResearch={onStartResearch}
                    onStartSandbox={onStartSandbox}
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
  type MetaRow = { label: string; value: string; isLink?: boolean };
  const rows: MetaRow[] = [];

  if (entry.source) rows.push({ label: "Source", value: entry.source });
  if (entry.added_at) rows.push({ label: "Added", value: entry.added_at });
  if (entry.url)
    rows.push({ label: "URL", value: entry.url, isLink: true });
  if (entry.account)
    rows.push({ label: "Account", value: `@${entry.account}` });
  if (entry.paper_url)
    rows.push({ label: "Paper", value: entry.paper_url, isLink: true });

  if (rows.length === 0) return null;

  return (
    <div className="space-y-2">
      {rows.map(({ label, value, isLink }, i) => (
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
          {isLink ? (
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

/** Shared prose styles for rendered markdown inside cards */
const markdownComponents = {
  p: ({ children }: { children?: React.ReactNode }) => (
    <p className="font-mono text-[11px] leading-relaxed text-text-secondary mb-2 last:mb-0">
      {children}
    </p>
  ),
  strong: ({ children }: { children?: React.ReactNode }) => (
    <strong className="font-bold text-white">{children}</strong>
  ),
  em: ({ children }: { children?: React.ReactNode }) => (
    <em className="italic text-text-secondary/80">{children}</em>
  ),
  a: ({ href, children }: { href?: string; children?: React.ReactNode }) => (
    <a
      href={href}
      target="_blank"
      rel="noopener noreferrer"
      className="text-accent-cyan hover:underline"
    >
      {children}
    </a>
  ),
  ul: ({ children }: { children?: React.ReactNode }) => (
    <ul className="space-y-1 mb-2 last:mb-0">{children}</ul>
  ),
  li: ({ children }: { children?: React.ReactNode }) => (
    <li className="font-mono text-[11px] text-text-secondary leading-relaxed">
      <span className="text-accent-cyan mr-2">•</span>
      {children}
    </li>
  ),
  code: ({ children }: { children?: React.ReactNode }) => (
    <code className="font-mono text-[11px] bg-surface-high px-1 py-0.5 text-accent-cyan">
      {children}
    </code>
  ),
};

/** Summary content based on source type */
function ExpandedSummary({ entry }: { entry: WorkbenchEntry }) {
  // Method: show description / "why it matters"
  if (entry.source_type === "method" && entry.description) {
    return (
      <div className="border-l-2 border-purple/50 bg-black/40 p-3">
        <p className="text-[10px] font-headline font-bold text-text-secondary uppercase tracking-[0.2em] mb-1">
          Why It Matters
        </p>
        <ReactMarkdown components={markdownComponents}>
          {entry.description}
        </ReactMarkdown>
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
            <ReactMarkdown components={markdownComponents}>
              {entry.caption.slice(0, 300) +
                (entry.caption.length > 300 ? "…" : "")}
            </ReactMarkdown>
          </div>
        )}
      </div>
    );
  }

  // Tool: show description or notes
  const toolContent = entry.description || entry.notes;
  if (toolContent) {
    return (
      <div className="border-l-2 border-accent-green/50 bg-black/40 p-3">
        <p className="text-[10px] font-headline font-bold text-text-secondary uppercase tracking-[0.2em] mb-1">
          {entry.description ? "What It Does" : "Notes"}
        </p>
        <ReactMarkdown components={markdownComponents}>
          {toolContent}
        </ReactMarkdown>
      </div>
    );
  }

  return null;
}

/** Status-specific action buttons */
function StatusActions({
  entry,
  onStartResearch,
  onStartSandbox,
  onViewLog,
  onViewReport,
  onPublishVault,
}: {
  entry: WorkbenchEntry;
  onStartResearch?: (key: string) => void;
  onStartSandbox?: (key: string) => void;
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

  if (entry.status === "sandbox_creating") {
    return (
      <div className="space-y-2">
        <div className="flex items-center gap-2 py-2">
          <div className="h-1.5 w-1.5 animate-ping rounded-full bg-accent-amber" aria-hidden="true" />
          <span className="text-[10px] font-bold uppercase tracking-widest text-accent-amber">
            BUILDING SANDBOX…
          </span>
        </div>
        <GlowButton
          variant="secondary"
          className="w-full py-1.5 text-[10px] tracking-widest"
          onClick={() => onViewReport?.(entry.key)}
        >
          VIEW RESEARCH
        </GlowButton>
      </div>
    );
  }

  if (entry.status === "sandbox_ready") {
    return (
      <div className="space-y-2">
        <div className="flex items-center gap-2 py-1">
          <span className="text-[10px] font-bold uppercase tracking-widest text-accent-green">
            ✓ SANDBOX READY
          </span>
        </div>
        <SandboxViewer entryKey={entry.key} status={entry.status} />
        <GlowButton
          variant="secondary"
          className="w-full py-1.5 text-[10px] tracking-widest"
          onClick={() => onViewReport?.(entry.key)}
        >
          VIEW RESEARCH
        </GlowButton>
        <button
          className={`w-full py-1.5 border font-heading text-[10px] font-bold uppercase transition-colors ${
            entry.vault_note
              ? "border-accent-green text-accent-green hover:text-white"
              : "border-outline-variant text-text-secondary/70 hover:text-white"
          }`}
          onClick={() => onPublishVault?.(entry.key)}
        >
          {entry.vault_note ? "OPEN IN VAULT" : "PUBLISH TO VAULT"}
        </button>
      </div>
    );
  }

  if (entry.status === "experiment_running") {
    return (
      <div className="space-y-2">
        <div className="flex items-center gap-2 py-2">
          <div className="h-1.5 w-1.5 animate-ping rounded-full bg-accent-amber" aria-hidden="true" />
          <span className="text-[10px] font-bold uppercase tracking-widest text-accent-amber">
            EXPERIMENT RUNNING…
          </span>
        </div>
        <SandboxViewer entryKey={entry.key} status={entry.status} />
        <GlowButton
          variant="secondary"
          className="w-full py-1.5 text-[10px] tracking-widest"
          onClick={() => onViewReport?.(entry.key)}
        >
          VIEW RESEARCH
        </GlowButton>
      </div>
    );
  }

  if (entry.status === "experiment_done") {
    return (
      <div className="space-y-2">
        <div className="flex items-center gap-2 py-1">
          <span className="text-[10px] font-bold uppercase tracking-widest text-accent-green">
            ✓ EXPERIMENT COMPLETE
          </span>
        </div>
        <SandboxViewer entryKey={entry.key} status={entry.status} />
        <GlowButton
          variant="secondary"
          className="w-full py-1.5 text-[10px] tracking-widest"
          onClick={() => onViewReport?.(entry.key)}
        >
          VIEW RESEARCH
        </GlowButton>
        <button
          className={`w-full py-1.5 border font-heading text-[10px] font-bold uppercase transition-colors ${
            entry.vault_note
              ? "border-accent-green text-accent-green hover:text-white"
              : "border-outline-variant text-text-secondary/70 hover:text-white"
          }`}
          onClick={() => onPublishVault?.(entry.key)}
        >
          {entry.vault_note ? "OPEN IN VAULT" : "PUBLISH TO VAULT"}
        </button>
      </div>
    );
  }

  if (entry.status === "researched" || entry.status === "completed") {
    return (
      <div className="space-y-2">
        <GlowButton
          variant="primary"
          className="w-full py-1.5 text-[10px] tracking-widest"
          onClick={() => onViewReport?.(entry.key)}
        >
          VIEW REPORT
        </GlowButton>
        {entry.verdict === "programmatic" && (
          <SandboxGate
            entry={entry}
            onStartSandbox={onStartSandbox}
          />
        )}
        <button
          className={`w-full py-1.5 border font-heading text-[10px] font-bold uppercase transition-colors ${
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
    );
  }

  return null;
}

/** Sandbox file tab labels and keys */
const SANDBOX_TABS = [
  { key: "experiment_plan", label: "EXPERIMENT PLAN" },
  { key: "run_sh", label: "RUN.SH" },
  { key: "dockerfile", label: "DOCKERFILE" },
  { key: "experiment_py", label: "EXPERIMENT.PY" },
  { key: "findings", label: "FINDINGS" },
] as const;

type SandboxFileKey = (typeof SANDBOX_TABS)[number]["key"];

interface SandboxFiles {
  experiment_plan: string | null;
  run_sh: string | null;
  dockerfile: string | null;
  experiment_py: string | null;
  requirements_txt: string | null;
  findings: string | null;
}

interface ExperimentResults {
  results: Record<string, unknown> | null;
  findings: string | null;
  log_tail: string;
  completed: boolean;
}

/**
 * SandboxViewer — fetches and displays sandbox output files in tabs,
 * with RUN EXPERIMENT button and results display.
 */
function SandboxViewer({ entryKey, status }: { entryKey: string; status: string }) {
  const isExperimentActive = status === "experiment_running";
  const [files, setFiles] = useState<SandboxFiles | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<SandboxFileKey>("experiment_plan");
  const [open, setOpen] = useState(isExperimentActive);
  const [running, setRunning] = useState(isExperimentActive);
  const [expResults, setExpResults] = useState<ExperimentResults | null>(null);

  const fetchFiles = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const url = `/api/research/sandbox-files/${encodeURIComponent(entryKey)}`;
      const res = await fetch(url);
      if (!res.ok) throw new Error(`Failed (${res.status})`);
      const data = await res.json();
      setFiles(data);
      setOpen(true);

      const { fetchExperimentResults } = await import("./hooks");
      const results = await fetchExperimentResults(entryKey);
      if (results.completed) {
        setExpResults(results);
        setRunning(false);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load");
    } finally {
      setLoading(false);
    }
  }, [entryKey]);

  // Auto-fetch files on mount when experiment is running
  useEffect(() => {
    if (isExperimentActive && !files) {
      fetchFiles();
    }
  }, [isExperimentActive, files, fetchFiles]);

  const handleOpen = useCallback(async () => {
    if (files) {
      setOpen((prev) => !prev);
      return;
    }
    await fetchFiles();
  }, [files, fetchFiles]);

  const handleRun = useCallback(async () => {
    setRunning(true);
    setError(null);
    try {
      const { runExperiment } = await import("./hooks");
      await runExperiment(entryKey);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to launch experiment");
      setRunning(false);
    }
  }, [entryKey]);

  const handleCheckResults = useCallback(async () => {
    try {
      const { fetchExperimentResults } = await import("./hooks");
      const results = await fetchExperimentResults(entryKey);
      setExpResults(results);
      if (results.completed) {
        setRunning(false);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to check results");
    }
  }, [entryKey]);

  const handleKill = useCallback(async () => {
    try {
      const { killExperiment } = await import("./hooks");
      await killExperiment(entryKey);
      setRunning(false);
      setError("Experiment killed.");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to kill experiment");
    }
  }, [entryKey]);

  // Poll for results while experiment is running
  useEffect(() => {
    if (!running) return;
    const interval = setInterval(handleCheckResults, 5000);
    return () => clearInterval(interval);
  }, [running, handleCheckResults]);

  const activeContent = files?.[activeTab];
  const r = expResults?.results as Record<string, string | number | boolean> | null;

  return (
    <div className="space-y-2">
      <GlowButton
        variant="primary"
        className="w-full py-2 text-xs tracking-widest"
        onClick={handleOpen}
        disabled={loading}
      >
        {loading ? "LOADING…" : open ? "HIDE EXPERIMENT" : "VIEW EXPERIMENT"}
      </GlowButton>

      {error && (
        <p className="text-[10px] font-mono text-accent-red">{error}</p>
      )}

      {open && files && (
        <div className="space-y-2">
          {/* Experiment results banner */}
          {expResults?.completed && r && (
            <div className={cn(
              "border p-3",
              r.passed
                ? "border-accent-green/30 bg-accent-green/5"
                : "border-accent-red/30 bg-accent-red/5"
            )}>
              <div className="flex items-center justify-between mb-2">
                <span className={cn(
                  "text-[10px] font-bold uppercase tracking-widest",
                  r.passed ? "text-accent-green" : "text-accent-red"
                )}>
                  {r.passed ? "✓ PASSED" : "✗ FAILED"}
                </span>
                <span className="text-[9px] font-mono text-text-muted">
                  {String(r.metric_name ?? "")}
                </span>
              </div>
              <div className="grid grid-cols-3 gap-3">
                <div>
                  <p className="text-[9px] font-mono text-text-muted uppercase">Result</p>
                  <p className="font-mono text-sm text-white font-bold">{String(r.result ?? "—")}</p>
                </div>
                {r.baseline != null && (
                  <div>
                    <p className="text-[9px] font-mono text-text-muted uppercase">Baseline</p>
                    <p className="font-mono text-sm text-text-secondary">{String(r.baseline)}</p>
                  </div>
                )}
                {r.improvement != null && (
                  <div>
                    <p className="text-[9px] font-mono text-text-muted uppercase">Delta</p>
                    <p className={cn(
                      "font-mono text-sm font-bold",
                      Number(r.improvement) > 0 ? "text-accent-green" : "text-accent-red"
                    )}>
                      {Number(r.improvement) > 0 ? "+" : ""}{String(r.improvement)}
                    </p>
                  </div>
                )}
              </div>
              {r.description && (
                <p className="mt-2 font-mono text-[11px] text-text-secondary">
                  {String(r.description)}
                </p>
              )}
            </div>
          )}

          {/* Findings */}
          {expResults?.findings && (
            <div className="border border-accent-green/20 bg-black/40 p-3 max-h-48 overflow-y-auto">
              <p className="text-[10px] font-headline font-bold text-accent-green uppercase tracking-[0.2em] mb-2">
                Findings
              </p>
              <pre className="font-mono text-[11px] text-text-secondary leading-relaxed whitespace-pre-wrap">
                {expResults.findings}
              </pre>
            </div>
          )}

          {/* Run / Kill experiment */}
          {!expResults?.completed && !running && (
            <button
              className="w-full py-1.5 bg-accent-cyan text-bg-base font-heading text-[10px] font-bold uppercase tracking-widest hover:bg-accent-cyan/80 transition-colors"
              onClick={handleRun}
            >
              RUN EXPERIMENT
            </button>
          )}
          {running && (
            <div className="flex gap-2">
              <div className="flex-1 flex items-center gap-2 px-3 py-1.5 border border-accent-cyan/30 bg-accent-cyan/5">
                <div className="h-1.5 w-1.5 animate-ping rounded-full bg-accent-cyan" aria-hidden="true" />
                <span className="text-[10px] font-bold uppercase tracking-widest text-accent-cyan">
                  RUNNING…
                </span>
              </div>
              <button
                className="px-3 py-1.5 border border-accent-red/50 text-accent-red font-heading text-[10px] font-bold uppercase tracking-widest hover:bg-accent-red/10 transition-colors"
                onClick={handleKill}
              >
                KILL
              </button>
            </div>
          )}

          {/* Log tail while running */}
          {running && expResults?.log_tail && (
            <div className="border border-outline-variant/20 bg-black/40 p-2 max-h-32 overflow-y-auto">
              <pre className="font-mono text-[10px] text-text-muted leading-relaxed whitespace-pre-wrap">
                {expResults.log_tail}
              </pre>
            </div>
          )}

          {/* File tabs */}
          <div className="border border-accent-green/20 bg-black/40">
            <div className="flex overflow-x-auto border-b border-outline-variant/20">
              {SANDBOX_TABS.filter((t) => files[t.key]).map((tab) => (
                <button
                  key={tab.key}
                  className={cn(
                    "px-3 py-1.5 text-[9px] font-heading font-bold uppercase tracking-widest whitespace-nowrap transition-colors",
                    activeTab === tab.key
                      ? "text-accent-green border-b-2 border-accent-green"
                      : "text-text-secondary hover:text-white"
                  )}
                  onClick={() => setActiveTab(tab.key)}
                >
                  {tab.label}
                </button>
              ))}
            </div>
            <div className="p-3 max-h-64 overflow-y-auto">
              {activeContent ? (
                <pre className="font-mono text-[11px] text-text-secondary leading-relaxed whitespace-pre-wrap">
                  {activeContent}
                </pre>
              ) : (
                <p className="text-[10px] font-mono text-text-muted italic">
                  No content for this file.
                </p>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

/**
 * SandboxGate — 3-stage review gate before launching sandbox.
 * Stage 1: "REVIEW EXPERIMENT" — fetches and shows experiment design
 * Stage 2: Cost acknowledgement (if cost_flagged)
 * Stage 3: "LAUNCH SANDBOX" — fires the sandbox API
 */
function SandboxGate({
  entry,
  onStartSandbox,
}: {
  entry: WorkbenchEntry;
  onStartSandbox?: (key: string) => void;
}) {
  const [experimentDesign, setExperimentDesign] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [costAcked, setCostAcked] = useState(entry.cost_approved ?? false);

  const reviewed = entry.reviewed ?? false;
  const costFlagged = entry.cost_flagged ?? false;
  const costCleared = !costFlagged || costAcked;

  const handleReview = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const { fetchExperimentDesign, markReviewed } = await import("./hooks");
      const content = await fetchExperimentDesign(entry.key);
      setExperimentDesign(content);
      await markReviewed(entry.key);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load experiment design");
    } finally {
      setLoading(false);
    }
  }, [entry.key]);

  const handleAcknowledgeCost = useCallback(async () => {
    try {
      const { acknowledgeCost } = await import("./hooks");
      await acknowledgeCost(entry.key);
      setCostAcked(true);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to acknowledge cost");
    }
  }, [entry.key]);

  // Stage 1: Not yet reviewed — show review button
  if (!reviewed && !experimentDesign) {
    return (
      <GlowButton
        variant="secondary"
        className="w-full py-2 text-xs tracking-widest"
        onClick={handleReview}
        disabled={loading}
      >
        {loading ? "LOADING…" : "REVIEW EXPERIMENT"}
      </GlowButton>
    );
  }

  return (
    <div className="space-y-3">
      {/* Experiment design preview */}
      {experimentDesign && (
        <div className="border border-accent-amber/30 bg-accent-amber/5 p-3 max-h-48 overflow-y-auto">
          <p className="text-[10px] font-headline font-bold text-accent-amber uppercase tracking-[0.2em] mb-2">
            Experiment Design
          </p>
          <div className="font-mono text-[11px] text-text-secondary leading-relaxed whitespace-pre-wrap">
            {experimentDesign}
          </div>
        </div>
      )}

      {/* Stage 2: Cost warning */}
      {costFlagged && !costAcked && (
        <div className="border border-accent-red/30 bg-accent-red/5 p-3 space-y-2">
          <p className="text-[10px] font-headline font-bold text-accent-red uppercase tracking-[0.2em]">
            Cost / Subscription Detected
          </p>
          {entry.cost_notes && (
            <p className="font-mono text-[11px] text-text-secondary italic">
              {entry.cost_notes}
            </p>
          )}
          <button
            className="w-full py-1.5 border border-accent-red/50 text-accent-red font-heading text-[10px] font-bold uppercase tracking-widest hover:bg-accent-red/10 transition-colors"
            onClick={handleAcknowledgeCost}
          >
            I ACKNOWLEDGE THE COST — PROCEED
          </button>
        </div>
      )}

      {/* Stage 3: Launch sandbox */}
      {costCleared && (
        <button
          className="w-full py-2 bg-accent-amber text-bg-base font-heading text-[10px] font-bold uppercase tracking-widest hover:bg-accent-amber/80 transition-colors"
          onClick={() => onStartSandbox?.(entry.key)}
        >
          LAUNCH SANDBOX
        </button>
      )}

      {error && (
        <p className="text-[10px] font-mono text-accent-red">{error}</p>
      )}
    </div>
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

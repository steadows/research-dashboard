"use client";

import { useState, useMemo, useCallback, useEffect, useRef } from "react";
import { useSWRConfig, mutate as swrMutate } from "swr";
import { GlowButton } from "@/components/ui/glow-button";
import { DataReadout } from "@/components/ui/data-readout";
import { apiMutate } from "@/lib/api";
import { useInstagramFeed } from "./hooks";
import { AgenticCardSkeleton, Skeleton } from "./Skeleton";
import type { InstagramPost } from "./types";

// ─── Refresh Progress Panel ───────────────────────────────────────────────────

const REFRESH_STEPS = [
  "CONNECTING TO META CLOUD",
  "FETCHING RECENT VIDEOS",
  "TRANSCRIBING CONTENT",
  "EXTRACTING KEYWORDS",
  "WRITING VAULT NOTES",
] as const;

// Approximate ms before each step advances (total ~10s before real response)
const STEP_DELAYS = [0, 1500, 3500, 6000, 8500];

interface RefreshStatusPanelProps {
  active: boolean;
  result: { notes_written: number } | null;
  onDismiss: () => void;
}

function RefreshStatusPanel({ active, result, onDismiss }: RefreshStatusPanelProps) {
  const [currentStep, setCurrentStep] = useState(0);
  const timersRef = useRef<ReturnType<typeof setTimeout>[]>([]);

  useEffect(() => {
    if (!active) {
      setCurrentStep(0);
      timersRef.current.forEach(clearTimeout);
      timersRef.current = [];
      return;
    }
    // Schedule step advances
    timersRef.current = STEP_DELAYS.map((delay, i) =>
      setTimeout(() => setCurrentStep(i), delay)
    );
    return () => timersRef.current.forEach(clearTimeout);
  }, [active]);

  if (!active && !result) return null;

  if (result) {
    return (
      <div className="border border-accent-green/40 bg-accent-green/5 p-4 flex items-center justify-between gap-4">
        <div className="flex items-center gap-3">
          <svg className="h-4 w-4 text-accent-green shrink-0" fill="currentColor" viewBox="0 0 24 24">
            <path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm-2 15l-5-5 1.41-1.41L10 14.17l7.59-7.59L19 8l-9 9z" />
          </svg>
          <span className="font-mono text-[11px] text-accent-green uppercase tracking-widest">
            SYNC COMPLETE &mdash; {result.notes_written} NOTE{result.notes_written !== 1 ? "S" : ""} WRITTEN
          </span>
        </div>
        <button
          onClick={onDismiss}
          className="text-[10px] font-mono text-text-muted hover:text-accent-cyan transition-colors"
        >
          DISMISS
        </button>
      </div>
    );
  }

  return (
    <div className="border border-accent-cyan/30 bg-bg-surface p-4 space-y-3">
      <div className="flex items-center gap-2 text-[10px] font-mono text-accent-cyan uppercase tracking-widest">
        <span className="h-2 w-2 rounded-full bg-accent-cyan animate-pulse shrink-0" />
        REFRESH IN PROGRESS
      </div>
      <div className="space-y-1.5">
        {REFRESH_STEPS.map((step, i) => {
          const done = i < currentStep;
          const active = i === currentStep;
          return (
            <div key={step} className="flex items-center gap-3">
              <span
                className={`shrink-0 h-1.5 w-1.5 rounded-full transition-colors ${
                  done
                    ? "bg-accent-green"
                    : active
                    ? "bg-accent-cyan animate-pulse"
                    : "bg-surface-high"
                }`}
              />
              <span
                className={`text-[10px] font-mono uppercase tracking-wider transition-colors ${
                  done
                    ? "text-accent-green/70"
                    : active
                    ? "text-accent-cyan"
                    : "text-text-muted"
                }`}
              >
                {step}
                {done && " \u2713"}
              </span>
            </div>
          );
        })}
      </div>
      {/* Progress bar */}
      <div className="h-px bg-surface-high w-full overflow-hidden">
        <div
          className="h-full bg-accent-cyan transition-all duration-700"
          style={{ width: `${Math.round(((currentStep + 1) / REFRESH_STEPS.length) * 100)}%` }}
        />
      </div>
    </div>
  );
}

// ─── Sub-components ──────────────────────────────────────────────────────────

function IntelCard({ post }: { post: InstagramPost }) {
  const isAnalyzed = post.status === "analyzed";
  const [summary, setSummary] = useState<string | null>(null);
  const [showSummary, setShowSummary] = useState(false);
  const [summarizing, setSummarizing] = useState(false);
  const [wbStatus, setWbStatus] = useState<"idle" | "sending" | "sent">("idle");
  const [dismissing, setDismissing] = useState(false);

  const handleDismiss = useCallback(async (e: React.MouseEvent) => {
    e.stopPropagation();
    if (dismissing) return;
    setDismissing(true);
    try {
      await apiMutate(`/status/instagram::${post.title}`, { body: { status: "dismissed" } });
      await swrMutate("/instagram/feed");
    } catch (err) {
      console.error("Dismiss failed:", err);
      setDismissing(false);
    }
  }, [post.title, dismissing]);

  const handleSummarize = useCallback(async () => {
    if (summarizing) return;

    // If already have a summary, just toggle visibility
    if (summary) {
      setShowSummary((prev) => !prev);
      return;
    }

    setSummarizing(true);
    try {
      const result = await apiMutate<{ summary: string }>(
        "/summarize/instagram",
        { body: { post } }
      );
      setSummary(result.summary);
      setShowSummary(true);
    } catch (err) {
      console.error("Summarize failed:", err);
    } finally {
      setSummarizing(false);
    }
  }, [post, summary, summarizing]);

  const handleWorkbench = useCallback(async () => {
    if (wbStatus !== "idle") return;
    setWbStatus("sending");
    try {
      await apiMutate("/workbench", {
        body: {
          item: {
            source_type: "instagram",
            name: post.title,
            ...post,
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
  }, [post, wbStatus]);

  return (
    <div
      className={`relative bg-bg-surface border-l-4 border-indigo p-5 flex flex-col gap-5 group hover:bg-surface-high/50 hover:box-glow-indigo transition-all duration-200 ${
        isAnalyzed ? "ring-1 ring-accent-cyan/30" : ""
      }`}
    >
      {/* Header */}
      <div className="space-y-1">
        <h3 className="font-headline font-bold text-xl text-white leading-tight uppercase tracking-tight">
          {post.title}
        </h3>
        <div className="flex justify-between items-center">
          <span className="text-[10px] font-mono text-accent-cyan uppercase tracking-wider">
            {post.account} &bull; {formatTimestamp(post.timestamp)}
          </span>
          {isAnalyzed && (
            <div className="flex items-center gap-1 text-accent-green">
              <svg className="h-3 w-3" fill="currentColor" viewBox="0 0 24 24">
                <path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm-2 15l-5-5 1.41-1.41L10 14.17l7.59-7.59L19 8l-9 9z" />
              </svg>
              <span className="text-[9px] font-mono uppercase">ANALYZED</span>
            </div>
          )}
        </div>
      </div>

      {/* Key Points */}
      {post.key_points.length > 0 && (
        <div className="space-y-2">
          <p className="text-[10px] font-headline font-bold text-text-secondary uppercase tracking-[0.2em] border-b border-outline-variant/20 pb-1">
            Key Points
          </p>
          <ul className="space-y-2">
            {post.key_points.map((point, i) => (
              <li key={i} className="flex gap-2 text-xs text-text-secondary">
                <span className="text-accent-cyan font-bold shrink-0">&raquo;</span>
                <span>{point}</span>
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* Transcript Excerpt */}
      {post.transcript_excerpt && (
        <div className="space-y-2">
          <p className="text-[10px] font-headline font-bold text-text-secondary uppercase tracking-[0.2em] border-b border-outline-variant/20 pb-1">
            Transcript Excerpt
          </p>
          <div className="bg-bg-base border border-outline-variant/10 p-3 font-mono text-[10px] text-accent-cyan/70 leading-relaxed italic">
            &ldquo;{post.transcript_excerpt}&rdquo;
          </div>
        </div>
      )}

      {/* Summary (expandable) */}
      {showSummary && summary && (
        <div className="space-y-2">
          <p className="text-[10px] font-headline font-bold text-accent-green uppercase tracking-[0.2em] border-b border-accent-green/20 pb-1">
            Summary
          </p>
          <div className="bg-bg-base border border-accent-green/20 p-3 text-xs text-text-secondary leading-relaxed">
            {summary}
          </div>
        </div>
      )}

      {/* Tags */}
      {post.tags.length > 0 && (
        <div className="flex flex-wrap gap-2 pt-2">
          {[...new Set(post.tags)].map((tag) => (
            <span
              key={tag}
              className="text-[9px] font-mono border border-accent-cyan/40 text-accent-cyan px-2 py-0.5"
            >
              {tag.toUpperCase()}
            </span>
          ))}
        </div>
      )}

      {/* Actions */}
      <div className="mt-auto pt-4 flex items-center gap-3">
        <GlowButton
          variant="secondary"
          className="py-2 text-[10px] px-4"
          onClick={handleDismiss}
          disabled={dismissing}
        >
          {dismissing ? "..." : "DISMISS"}
        </GlowButton>
        {isAnalyzed || summary ? (
          <GlowButton
            variant="primary"
            className="flex-1 py-2 text-[10px]"
            onClick={handleSummarize}
          >
            {showSummary ? "HIDE SUMMARY" : "VIEW SUMMARY"}
          </GlowButton>
        ) : (
          <GlowButton
            variant="secondary"
            className="flex-1 py-2 text-[10px]"
            onClick={handleSummarize}
            disabled={summarizing}
          >
            {summarizing ? "ANALYZING..." : "SUMMARIZE"}
          </GlowButton>
        )}
        <button
          onClick={handleWorkbench}
          disabled={wbStatus !== "idle"}
          className={`flex-1 py-2 text-[10px] font-headline font-bold uppercase tracking-widest transition-all ${
            wbStatus === "sent"
              ? "bg-accent-green text-bg-base"
              : "bg-indigo text-white hover:opacity-90"
          } ${wbStatus === "sending" ? "opacity-60" : ""}`}
        >
          {wbStatus === "sent"
            ? "SENT"
            : wbStatus === "sending"
              ? "SENDING..."
              : "WORKBENCH"}
        </button>
      </div>
    </div>
  );
}

function SignalAnalysisSidebar({ posts }: { posts: InstagramPost[] }) {
  const accountCounts = useMemo(() => {
    const counts: Record<string, number> = {};
    for (const post of posts) {
      counts[post.account] = (counts[post.account] ?? 0) + 1;
    }
    return Object.entries(counts).sort((a, b) => b[1] - a[1]);
  }, [posts]);

  const tagCounts = useMemo(() => {
    const counts: Record<string, number> = {};
    for (const post of posts) {
      for (const tag of post.tags) {
        counts[tag] = (counts[tag] ?? 0) + 1;
      }
    }
    return Object.entries(counts)
      .sort((a, b) => b[1] - a[1])
      .slice(0, 5);
  }, [posts]);

  const maxTagCount = tagCounts[0]?.[1] ?? 1;

  return (
    <aside className="w-full lg:w-80 shrink-0">
      <div className="bg-bg-surface border border-accent-cyan/20 p-6 flex flex-col gap-6 sticky top-4">
        <div>
          <h2 className="font-headline font-bold text-accent-cyan uppercase tracking-widest text-sm mb-1">
            SIGNAL ANALYSIS
          </h2>
          <p className="font-mono text-[10px] text-text-muted">[01] SYSTEM: ONLINE</p>
        </div>

        {/* Stats */}
        <div className="grid grid-cols-2 gap-4">
          <div className="bg-surface-high/30 p-4 border border-outline-variant/10">
            <DataReadout label="TOTAL INGESTED" value={posts.length} color="cyan" />
          </div>
          <div className="bg-surface-high/30 p-4 border border-outline-variant/10">
            <DataReadout
              label="ACTIVE NODES"
              value={String(accountCounts.length).padStart(2, "0")}
              color="green"
            />
          </div>
        </div>

        {/* Posts by Source */}
        <div className="space-y-3">
          <p className="text-[10px] font-headline text-text-secondary uppercase tracking-widest">
            POSTS BY SOURCE
          </p>
          <div className="space-y-2">
            {accountCounts.map(([account, count]) => (
              <div key={account} className="space-y-1">
                <div className="flex justify-between text-[9px] font-mono text-text-secondary">
                  <span>{account}</span>
                  <span>{count}</span>
                </div>
                <div className="h-1 bg-surface-high w-full">
                  <div
                    className="h-full bg-accent-cyan shadow-[0_0_4px_#00F0FF]"
                    style={{
                      width: `${Math.round((count / (accountCounts[0]?.[1] ?? 1)) * 100)}%`,
                    }}
                  />
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Hot Keywords */}
        {tagCounts.length > 0 && (
          <div className="space-y-3">
            <p className="text-[10px] font-headline text-text-secondary uppercase tracking-widest">
              HOT KEYWORDS (7D)
            </p>
            <div className="flex flex-col gap-2">
              {tagCounts.map(([tag, count]) => (
                <div key={tag} className="flex items-center gap-3">
                  <span className="w-14 text-[9px] font-mono text-text-secondary truncate">
                    {tag.toUpperCase()}
                  </span>
                  <div className="flex-1 h-3 bg-surface-high relative">
                    <div
                      className="absolute inset-y-0 left-0 bg-accent-cyan/60 border-r border-accent-cyan"
                      style={{ width: `${Math.round((count / maxTagCount) * 100)}%` }}
                    />
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Sync indicator */}
        <div className="mt-4 pt-4 border-t border-outline-variant/20">
          <div className="flex items-center gap-2 text-[10px] font-mono text-text-secondary mb-2">
            <span className="h-2 w-2 rounded-full bg-accent-green animate-pulse" />
            SYNCHRONIZING WITH META CLOUD...
          </div>
          <div className="h-1 bg-surface-high w-full overflow-hidden">
            <div className="h-full bg-accent-green w-[72%]" />
          </div>
        </div>
      </div>
    </aside>
  );
}

// ─── Helpers ──────────────────────────────────────────────────────────────────

function formatTimestamp(ts: string): string {
  try {
    // Date-only strings ("2026-03-26") are parsed as UTC midnight by Date constructor,
    // which skews relative time in local timezones. Append T12:00 to anchor mid-day local.
    const normalized = /^\d{4}-\d{2}-\d{2}$/.test(ts) ? `${ts}T12:00` : ts;
    const date = new Date(normalized);
    const now = new Date();
    const diffMs = now.getTime() - date.getTime();
    const diffH = Math.floor(diffMs / 3_600_000);
    if (diffH < 1) return "JUST NOW";
    if (diffH < 24) return `${diffH}H AGO`;
    const diffD = Math.floor(diffH / 24);
    return `${diffD}D AGO`;
  } catch {
    return ts;
  }
}

// ─── Main Component ──────────────────────────────────────────────────────────

/**
 * AgenticHubTab — Instagram intelligence feed with signal analysis sidebar.
 * Matches agentic-hub.html Stitch design (text-only, no thumbnails).
 */
export function AgenticHubTab() {
  const { data, isLoading } = useInstagramFeed();
  const { mutate } = useSWRConfig();
  const [accountFilter, setAccountFilter] = useState<string>("all");
  const [refreshing, setRefreshing] = useState(false);
  const [refreshResult, setRefreshResult] = useState<{ notes_written: number } | null>(null);

  const accounts = useMemo(() => {
    if (!data) return [];
    return [...new Set(data.map((p) => p.account))];
  }, [data]);

  const filtered = data?.filter(
    (p) => accountFilter === "all" || p.account === accountFilter
  );

  const handleRefresh = useCallback(async () => {
    if (refreshing) return;
    setRefreshing(true);
    setRefreshResult(null);
    try {
      const targets =
        accountFilter === "all" ? accounts : [accountFilter];

      // Fire off all ingestion jobs (returns 202 immediately)
      await Promise.all(
        targets.map((username) =>
          apiMutate("/instagram/refresh", { body: { username, days: 14 } })
        )
      );

      // Show progress animation for a few seconds, then revalidate feed
      await new Promise((r) => setTimeout(r, 5000));
      await mutate("/instagram/feed");
      setRefreshResult({ notes_written: 0 });
    } catch (err) {
      console.error("Refresh failed:", err);
    } finally {
      setRefreshing(false);
    }
  }, [accountFilter, accounts, mutate, refreshing]);

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-end justify-between gap-4">
        <div>
          <h2 className="font-headline text-2xl font-bold uppercase tracking-widest text-accent-cyan mb-1">
            AGENTIC HUB
          </h2>
          <p className="font-mono text-[10px] text-text-secondary tracking-tighter opacity-70">
            [CHANNEL_01] INSTAGRAM INTELLIGENCE FEED
          </p>
        </div>
        <div className="flex flex-wrap gap-3 items-center">
          <GlowButton
            variant="secondary"
            className="py-1.5 px-4 text-[10px]"
            onClick={handleRefresh}
            disabled={refreshing || (accountFilter === "all" && accounts.length === 0)}
          >
            {refreshing ? "REFRESHING..." : "REFRESH FEED"}
          </GlowButton>
          <div className="flex bg-bg-surface p-1 border border-outline-variant/30">
            <button
              onClick={() => setAccountFilter("all")}
              className={`px-3 py-1 text-[10px] font-headline transition-colors ${
                accountFilter === "all"
                  ? "bg-accent-cyan text-bg-base"
                  : "text-text-secondary hover:text-accent-cyan"
              }`}
            >
              ALL
            </button>
            {accounts.map((acct) => (
              <button
                key={acct}
                onClick={() => setAccountFilter(acct)}
                className={`px-3 py-1 text-[10px] font-headline transition-colors ${
                  accountFilter === acct
                    ? "bg-accent-cyan text-bg-base"
                    : "text-text-secondary hover:text-accent-cyan"
                }`}
              >
                {acct}
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* Refresh Status */}
      <RefreshStatusPanel
        active={refreshing}
        result={refreshResult}
        onDismiss={() => setRefreshResult(null)}
      />

      {/* Content + Sidebar */}
      <div className="flex flex-col lg:flex-row gap-8">
        {/* Cards Grid */}
        <div className="flex-1">
          {isLoading || !filtered ? (
            <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-6">
              <AgenticCardSkeleton />
              <AgenticCardSkeleton />
              <AgenticCardSkeleton />
            </div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-6">
              {filtered.map((post) => (
                <IntelCard key={post.id} post={post} />
              ))}
              {filtered.length === 0 && (
                <p className="font-mono text-sm text-text-secondary col-span-3">
                  No posts match the current filter
                </p>
              )}
            </div>
          )}
        </div>

        {/* Signal Analysis Sidebar */}
        {data && data.length > 0 && <SignalAnalysisSidebar posts={data} />}
        {isLoading && (
          <aside className="w-full lg:w-80 shrink-0">
            <div className="bg-bg-surface border border-accent-cyan/20 p-6 space-y-4">
              <Skeleton className="h-5 w-32" />
              <Skeleton className="h-3 w-24" />
              <div className="grid grid-cols-2 gap-4">
                <Skeleton className="h-16" />
                <Skeleton className="h-16" />
              </div>
              <Skeleton className="h-24" />
            </div>
          </aside>
        )}
      </div>
    </div>
  );
}

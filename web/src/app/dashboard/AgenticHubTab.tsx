"use client";

import { useState, useMemo } from "react";
import { GlowButton } from "@/components/ui/glow-button";
import { DataReadout } from "@/components/ui/data-readout";
import { useInstagramFeed } from "./hooks";
import { AgenticCardSkeleton, Skeleton } from "./Skeleton";
import type { InstagramPost } from "./types";

// ─── Sub-components ──────────────────────────────────────────────────────────

function IntelCard({ post }: { post: InstagramPost }) {
  const isAnalyzed = post.status === "analyzed";

  return (
    <div
      className={`relative bg-bg-surface border-l-4 border-indigo p-5 flex flex-col gap-5 group hover:bg-surface-high/50 transition-all duration-150 ${
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

      {/* Tags */}
      {post.tags.length > 0 && (
        <div className="flex flex-wrap gap-2 pt-2">
          {post.tags.map((tag) => (
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
        {isAnalyzed ? (
          <GlowButton variant="primary" className="flex-1 py-2 text-[10px]">
            VIEW SUMMARY
          </GlowButton>
        ) : (
          <GlowButton variant="secondary" className="flex-1 py-2 text-[10px]">
            SUMMARIZE
          </GlowButton>
        )}
        <button className="flex-1 bg-indigo text-white py-2 text-[10px] font-headline font-bold uppercase tracking-widest hover:opacity-90 transition-opacity">
          WORKBENCH
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
    const date = new Date(ts);
    const now = new Date();
    const diffMs = now.getTime() - date.getTime();
    const diffH = Math.floor(diffMs / 3_600_000);
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
  const [accountFilter, setAccountFilter] = useState<string>("all");

  const accounts = useMemo(() => {
    if (!data) return [];
    return [...new Set(data.map((p) => p.account))];
  }, [data]);

  const filtered = data?.filter(
    (p) => accountFilter === "all" || p.account === accountFilter
  );

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

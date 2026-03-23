"use client";

import { useState, useCallback } from "react";
import useSWR, { mutate as swrMutate } from "swr";
import { AnimatePresence, m, useReducedMotion } from "framer-motion";
import { Badge } from "@/components/ui/badge";
import { GlowButton } from "@/components/ui/glow-button";
import { defaultSWRConfig, apiMutate } from "@/lib/api";
import { FeedSkeleton } from "@/app/dashboard/Skeleton";

interface ArchivedItem {
  key: string;
  type: string;
  name: string;
  status: string;
  notes?: string;
  category?: string;
  source?: string;
}

type FilterType = "all" | "tool" | "method" | "paper" | "blog" | "instagram";

const TYPE_COLORS: Record<string, string> = {
  tool: "border-accent-amber",
  method: "border-purple",
  paper: "border-accent-green",
  blog: "border-accent-cyan",
  instagram: "border-indigo",
};

const TYPE_BADGES: Record<string, { variant: "tool" | "method" | "journalclub" | "tldr" | "instagram" | "default"; label: string }> = {
  tool: { variant: "tool", label: "TOOL" },
  method: { variant: "method", label: "METHOD" },
  paper: { variant: "journalclub", label: "PAPER" },
  blog: { variant: "default", label: "BLOG" },
  instagram: { variant: "instagram", label: "INSTAGRAM" },
};

function ArchivedCard({
  item,
}: {
  item: ArchivedItem;
}) {
  const reduceMotion = useReducedMotion();
  const [hovered, setHovered] = useState(false);
  const [restoring, setRestoring] = useState(false);

  const handleRestore = useCallback(async (e: React.MouseEvent) => {
    e.stopPropagation();
    if (restoring) return;
    setRestoring(true);
    try {
      await apiMutate(`/status/archive/${item.key}`, { method: "DELETE" });
      await swrMutate("/status/archive");
      // Revalidate the source list so restored item appears
      const typeEndpoints: Record<string, string> = {
        tool: "/tools",
        method: "/methods",
        paper: "/papers",
        blog: "/blog-queue",
        instagram: "/instagram/feed",
      };
      const endpoint = typeEndpoints[item.type];
      if (endpoint) await swrMutate(endpoint);
    } catch (err) {
      console.error("Restore failed:", err);
      setRestoring(false);
    }
  }, [item, restoring]);

  const borderColor = TYPE_COLORS[item.type] ?? "border-outline-variant";
  const badge = TYPE_BADGES[item.type] ?? { variant: "default" as const, label: item.type.toUpperCase() };

  return (
    <div
      onMouseEnter={() => setHovered(true)}
      onMouseLeave={() => setHovered(false)}
      className={`bg-bg-surface border-l-4 ${borderColor} group hover:bg-surface-high/50 transition-all duration-200 opacity-70 hover:opacity-100`}
    >
      <div className="p-5 pb-3">
        <div className="flex justify-between items-start gap-3">
          <h3 className="font-mono font-bold text-sm text-white/70 group-hover:text-white transition-colors truncate">
            {item.name}
          </h3>
          <Badge variant={badge.variant}>{badge.label}</Badge>
        </div>
      </div>

      <AnimatePresence>
        {hovered && (
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
              {item.notes && (
                <p className="font-mono text-[11px] text-text-secondary leading-relaxed">
                  {item.notes}
                </p>
              )}
              {item.category && (
                <p className="font-mono text-[10px] text-outline">
                  Category: {item.category}
                </p>
              )}
              {item.source && (
                <p className="font-mono text-[10px] text-outline">
                  Source: {item.source}
                </p>
              )}

              <div className="pt-2 border-t border-outline-variant/20">
                <GlowButton
                  variant="secondary"
                  className="py-2 px-4 text-[10px]"
                  onClick={handleRestore}
                  disabled={restoring}
                >
                  {restoring ? "RESTORING..." : "RESTORE"}
                </GlowButton>
              </div>
            </div>
          </m.div>
        )}
      </AnimatePresence>
    </div>
  );
}

export default function ArchivePage() {
  const { data, isLoading } = useSWR<ArchivedItem[]>("/status/archive", defaultSWRConfig);
  const [filter, setFilter] = useState<FilterType>("all");

  const filtered = data?.filter((item) => filter === "all" || item.type === filter);

  // Get unique types present in data for filter buttons
  const availableTypes = data
    ? [...new Set(data.map((item) => item.type))].sort()
    : [];

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between border-b border-outline-variant/30 pb-2">
        <div>
          <h2 className="font-headline font-bold text-lg tracking-widest text-cyan-fixed uppercase">
            Archive
          </h2>
          <p className="font-mono text-[10px] text-text-secondary mt-1">
            DISMISSED ITEMS — RESTORE TO RETURN TO ACTIVE FEEDS
          </p>
        </div>
        <span className="font-mono text-[10px] text-outline">
          {filtered ? `${filtered.length} ITEMS` : "LOADING..."}
        </span>
      </div>

      {/* Filters */}
      {availableTypes.length > 1 && (
        <div className="flex bg-bg-surface p-1 border border-outline-variant/30 w-fit">
          <button
            onClick={() => setFilter("all")}
            className={`px-3 py-1 text-[10px] font-headline uppercase tracking-wider transition-colors ${
              filter === "all"
                ? "bg-accent-cyan text-bg-base"
                : "text-text-secondary hover:text-accent-cyan"
            }`}
          >
            ALL
          </button>
          {availableTypes.map((type) => (
            <button
              key={type}
              onClick={() => setFilter(type as FilterType)}
              className={`px-3 py-1 text-[10px] font-headline uppercase tracking-wider transition-colors ${
                filter === type
                  ? "bg-accent-cyan text-bg-base"
                  : "text-text-secondary hover:text-accent-cyan"
              }`}
            >
              {type === "instagram" ? "IG" : type}
            </button>
          ))}
        </div>
      )}

      {isLoading || !filtered ? (
        <FeedSkeleton count={3} />
      ) : filtered.length === 0 ? (
        <div className="bg-bg-surface border border-outline-variant/20 p-8 text-center">
          <p className="font-mono text-sm text-text-secondary">
            {data?.length === 0
              ? "Archive is empty — dismissed items will appear here"
              : "No items match the current filter"}
          </p>
        </div>
      ) : (
        <div className="space-y-3 max-h-[700px] overflow-y-auto p-2 -m-2">
          {filtered.map((item, i) => (
            <ArchivedCard
              key={item.key}
              item={item}
            />
          ))}
        </div>
      )}
    </div>
  );
}

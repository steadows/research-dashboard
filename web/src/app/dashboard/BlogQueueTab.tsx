"use client";

import { useState, useCallback } from "react";
import { Badge } from "@/components/ui/badge";
import { GlowButton } from "@/components/ui/glow-button";
import { apiMutate } from "@/lib/api";
import { useBlogQueue } from "./hooks";
import { FeedSkeleton } from "./Skeleton";
import type { BlogItem } from "./types";

function BlogCard({ item, index }: { item: BlogItem; index: number }) {
  const [expanded, setExpanded] = useState(false);
  const [draft, setDraft] = useState<string | null>(null);
  const [drafting, setDrafting] = useState(false);

  const statusColor =
    item.status === "draft"
      ? "text-accent-amber"
      : item.status === "published"
        ? "text-accent-green"
        : "text-outline";

  const handleGenerateDraft = useCallback(async () => {
    if (drafting) return;
    if (draft) {
      setExpanded(true);
      return;
    }
    setDrafting(true);
    try {
      const result = await apiMutate<{ draft: string; draft_path: string }>(
        "/blog-queue/draft",
        { body: { item: { name: item.title, hook: item.notes, tags: item.tags?.join(", ") ?? "" } } }
      );
      setDraft(result.draft);
      setExpanded(true);
    } catch (err) {
      console.error("Draft generation failed:", err);
    } finally {
      setDrafting(false);
    }
  }, [item, draft, drafting]);

  return (
    <div
      className={`bg-bg-surface p-5 border-l-4 border-accent-amber group transition-all duration-150 cursor-pointer ${
        expanded ? "ring-1 ring-accent-amber/30" : "hover:bg-surface-high/50"
      }`}
      onClick={() => setExpanded((prev) => !prev)}
    >
      <div className="flex justify-between items-start mb-2">
        <div className="flex items-center gap-3">
          <span className="font-mono text-[10px] text-accent-cyan/50">
            [{String(index + 1).padStart(2, "0")}]
          </span>
          <h3 className="font-mono font-bold text-white group-hover:text-accent-cyan transition-colors">
            {item.title}
          </h3>
        </div>
        <span className={`font-headline text-[9px] uppercase tracking-wider ${statusColor}`}>
          {item.status?.toUpperCase() ?? "QUEUED"}
        </span>
      </div>

      {item.category && (
        <Badge variant="tldr" className="mr-2 mb-2">{item.category}</Badge>
      )}

      {item.tags && item.tags.length > 0 && (
        <div className="flex flex-wrap gap-1.5 mt-2">
          {item.tags.map((tag) => (
            <span
              key={tag}
              className="text-[9px] font-mono border border-accent-cyan/40 text-accent-cyan px-2 py-0.5"
            >
              {tag.toUpperCase()}
            </span>
          ))}
        </div>
      )}

      {item.notes && (
        <p className="font-mono text-[11px] text-text-secondary mt-3 leading-relaxed">
          {item.notes}
        </p>
      )}

      {/* Expanded content */}
      {expanded && (
        <div className="mt-4 pt-4 border-t border-outline-variant/20 space-y-4" onClick={(e) => e.stopPropagation()}>
          {item.source && (
            <div>
              <p className="text-[10px] font-headline font-bold text-text-secondary uppercase tracking-[0.2em] mb-1">
                Source
              </p>
              <p className="font-mono text-[11px] text-accent-cyan/70">{item.source}</p>
            </div>
          )}

          {/* Draft content */}
          {draft && (
            <div className="space-y-2">
              <p className="text-[10px] font-headline font-bold text-accent-green uppercase tracking-[0.2em] border-b border-accent-green/20 pb-1">
                Generated Draft
              </p>
              <div className="bg-bg-base border border-accent-green/20 p-3 text-xs text-text-secondary leading-relaxed max-h-80 overflow-y-auto whitespace-pre-wrap">
                {draft}
              </div>
            </div>
          )}

          {/* Actions */}
          <div className="flex gap-3">
            <GlowButton
              variant="primary"
              className="flex-1 py-2 text-[10px]"
              onClick={handleGenerateDraft}
              disabled={drafting}
            >
              {drafting ? "GENERATING..." : draft ? "VIEW DRAFT" : "GENERATE DRAFT"}
            </GlowButton>
          </div>
        </div>
      )}
    </div>
  );
}

/**
 * BlogQueueTab — Blog ideas queue with expandable cards and draft generation.
 */
export function BlogQueueTab() {
  const { data, isLoading } = useBlogQueue();

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between border-b border-outline-variant/30 pb-2">
        <h2 className="font-headline font-bold text-lg tracking-widest text-cyan-fixed uppercase">
          Blog Queue
        </h2>
        <span className="font-mono text-[10px] text-outline">
          {data ? `${data.length} ITEMS` : "LOADING..."}
        </span>
      </div>

      {isLoading || !data ? (
        <FeedSkeleton count={5} />
      ) : (
        <div className="space-y-4 max-h-[700px] overflow-y-auto pr-2">
          {data.map((item, i) => (
            <BlogCard key={i} item={item} index={i} />
          ))}
          {data.length === 0 && (
            <p className="font-mono text-sm text-text-secondary">
              Blog queue is empty
            </p>
          )}
        </div>
      )}
    </div>
  );
}

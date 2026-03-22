"use client";

import { Badge } from "@/components/ui/badge";
import { useBlogQueue } from "./hooks";
import { FeedSkeleton } from "./Skeleton";
import type { BlogItem } from "./types";

function BlogCard({ item, index }: { item: BlogItem; index: number }) {
  const statusColor =
    item.status === "draft"
      ? "text-accent-amber"
      : item.status === "published"
        ? "text-accent-green"
        : "text-outline";

  return (
    <div className="bg-bg-surface p-5 border-l-4 border-accent-amber group hover:bg-surface-high/50 transition-colors">
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
    </div>
  );
}

/**
 * BlogQueueTab — Blog ideas queue with status indicators.
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

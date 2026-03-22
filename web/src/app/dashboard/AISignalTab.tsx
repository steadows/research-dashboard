"use client";

import { useMethods } from "./hooks";
import { Badge } from "@/components/ui/badge";
import { FeedSkeleton } from "./Skeleton";
import type { MethodItem } from "./types";

function MethodCard({ item, index }: { item: MethodItem; index: number }) {
  return (
    <div className="bg-bg-surface p-5 border-l-4 border-purple group hover:bg-surface-high/50 transition-colors">
      <div className="flex justify-between items-start mb-2">
        <div className="flex items-center gap-3">
          <span className="font-mono text-[10px] text-accent-cyan/50">
            [{String(index + 1).padStart(2, "0")}]
          </span>
          <h3 className="font-mono font-bold text-white group-hover:text-accent-cyan transition-colors">
            {item.name}
          </h3>
        </div>
        <Badge variant="method">METHOD</Badge>
      </div>

      {item.category && (
        <span className="text-[9px] font-headline text-outline border border-outline-variant px-1.5 py-0.5 mr-2">
          {item.category.toUpperCase()}
        </span>
      )}

      {item.source && (
        <span className="text-[9px] font-mono text-accent-cyan/60 ml-1">
          via {item.source}
        </span>
      )}

      {item.tags && item.tags.length > 0 && (
        <div className="flex flex-wrap gap-1.5 mt-3">
          {item.tags.map((tag) => (
            <span
              key={tag}
              className="text-[9px] font-mono border border-purple/40 text-purple px-2 py-0.5"
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
 * AISignalTab — Methods/techniques intelligence feed from JournalClub.
 */
export function AISignalTab() {
  const { data, isLoading } = useMethods();

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between border-b border-outline-variant/30 pb-2">
        <h2 className="font-headline font-bold text-lg tracking-widest text-cyan-fixed uppercase">
          AI Signal
        </h2>
        <span className="font-mono text-[10px] text-outline">
          {data ? `${data.length} METHODS` : "LOADING..."}
        </span>
      </div>

      <p className="font-mono text-[10px] text-text-secondary">
        METHODS &amp; TECHNIQUES FROM JOURNALCLUB REPORTS
      </p>

      {isLoading || !data ? (
        <FeedSkeleton count={5} />
      ) : (
        <div className="grid grid-cols-1 gap-4 md:grid-cols-2 max-h-[700px] overflow-y-auto pr-2">
          {data.map((item, i) => (
            <MethodCard key={i} item={item} index={i} />
          ))}
          {data.length === 0 && (
            <p className="font-mono text-sm text-text-secondary col-span-2">
              No methods tracked
            </p>
          )}
        </div>
      )}
    </div>
  );
}

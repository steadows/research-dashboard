"use client";

import { useState } from "react";
import { Badge } from "@/components/ui/badge";
import { useTools } from "./hooks";
import { FeedSkeleton } from "./Skeleton";
import type { ToolItem } from "./types";

function ToolCard({ tool, index }: { tool: ToolItem; index: number }) {
  const dotColor =
    tool.status === "offline"
      ? "bg-accent-red"
      : tool.source === "tldr"
        ? "bg-accent-amber shadow-[0_0_5px_#ffbf00]"
        : "bg-accent-green shadow-[0_0_5px_#39ff14]";

  return (
    <div className="bg-bg-surface p-5 border-l-4 border-accent-green group hover:bg-surface-high/50 transition-colors">
      <div className="flex justify-between items-start mb-2">
        <div className="flex items-center gap-3">
          <div className={`h-2 w-2 shrink-0 rounded-full ${dotColor}`} />
          <h3 className="font-mono font-bold text-white group-hover:text-accent-cyan transition-colors">
            {tool.name}
          </h3>
        </div>
        <span className="font-mono text-[10px] text-accent-cyan/50">
          [{String(index + 1).padStart(2, "0")}]
        </span>
      </div>

      {tool.category && (
        <Badge variant="tool" className="mr-2 mb-2">{tool.category}</Badge>
      )}

      {tool.tags && tool.tags.length > 0 && (
        <div className="flex flex-wrap gap-1.5 mt-2">
          {tool.tags.map((tag) => (
            <span
              key={tag}
              className="text-[9px] font-mono border border-accent-cyan/40 text-accent-cyan px-2 py-0.5"
            >
              {tag.toUpperCase()}
            </span>
          ))}
        </div>
      )}

      {tool.notes && (
        <p className="font-mono text-[11px] text-text-secondary mt-3 leading-relaxed">
          {tool.notes}
        </p>
      )}
    </div>
  );
}

/**
 * ToolsRadarTab — Full tools radar view with category filter.
 */
export function ToolsRadarTab() {
  const { data, isLoading } = useTools();
  const [categoryFilter, setCategoryFilter] = useState<string>("all");

  const categories = data
    ? ["all", ...new Set(data.map((t) => t.category).filter(Boolean) as string[])]
    : ["all"];

  const filtered = data?.filter(
    (t) => categoryFilter === "all" || t.category === categoryFilter
  );

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between border-b border-outline-variant/30 pb-2">
        <h2 className="font-headline font-bold text-lg tracking-widest text-cyan-fixed uppercase">
          Tools Radar
        </h2>
        <span className="font-mono text-[10px] text-outline">
          {filtered ? `${filtered.length} TOOLS` : "LOADING..."}
        </span>
      </div>

      {/* Category filter */}
      {categories.length > 1 && (
        <div className="flex flex-wrap gap-2">
          {categories.map((cat) => (
            <button
              key={cat}
              onClick={() => setCategoryFilter(cat)}
              className={`px-3 py-1 text-[10px] font-headline uppercase tracking-wider border transition-colors ${
                categoryFilter === cat
                  ? "bg-accent-cyan text-bg-base border-accent-cyan"
                  : "border-outline-variant/30 text-text-secondary hover:text-accent-cyan hover:border-accent-cyan/50"
              }`}
            >
              {cat}
            </button>
          ))}
        </div>
      )}

      {isLoading || !filtered ? (
        <FeedSkeleton count={5} />
      ) : (
        <div className="grid grid-cols-1 gap-4 md:grid-cols-2 max-h-[700px] overflow-y-auto pr-2">
          {filtered.map((tool, i) => (
            <ToolCard key={i} tool={tool} index={i} />
          ))}
          {filtered.length === 0 && (
            <p className="font-mono text-sm text-text-secondary col-span-2">
              No tools match the current filter
            </p>
          )}
        </div>
      )}
    </div>
  );
}

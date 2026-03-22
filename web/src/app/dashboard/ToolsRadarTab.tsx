"use client";

import { useState, useCallback } from "react";
import { Badge } from "@/components/ui/badge";
import { GlowButton } from "@/components/ui/glow-button";
import { apiMutate } from "@/lib/api";
import { useTools } from "./hooks";
import { FeedSkeleton } from "./Skeleton";
import type { ToolItem } from "./types";

function ToolCard({ tool, index }: { tool: ToolItem; index: number }) {
  const [expanded, setExpanded] = useState(false);
  const [wbStatus, setWbStatus] = useState<"idle" | "sending" | "sent">("idle");

  const dotColor =
    tool.status === "offline"
      ? "bg-accent-red"
      : tool.source === "tldr"
        ? "bg-accent-amber shadow-[0_0_5px_#ffbf00]"
        : "bg-accent-green shadow-[0_0_5px_#39ff14]";

  const handleWorkbench = useCallback(async () => {
    if (wbStatus !== "idle") return;
    setWbStatus("sending");
    try {
      await apiMutate("/workbench", {
        body: {
          item: {
            source_type: "tool",
            name: tool.name,
            category: tool.category,
            status: tool.status,
            source: tool.source,
            notes: tool.notes,
            tags: tool.tags?.join(", ") ?? "",
          },
        },
      });
      setWbStatus("sent");
      setTimeout(() => setWbStatus("idle"), 2000);
    } catch (err) {
      console.error("Workbench send failed:", err);
      setWbStatus("idle");
    }
  }, [tool, wbStatus]);

  return (
    <div
      className={`bg-bg-surface p-5 border-l-4 border-accent-green group transition-all duration-150 cursor-pointer ${
        expanded ? "ring-1 ring-accent-green/30" : "hover:bg-surface-high/50"
      }`}
      onClick={() => setExpanded((prev) => !prev)}
    >
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

      {/* Expanded content */}
      {expanded && (
        <div className="mt-4 pt-4 border-t border-outline-variant/20 space-y-4" onClick={(e) => e.stopPropagation()}>
          {tool.source && (
            <div>
              <p className="text-[10px] font-headline font-bold text-text-secondary uppercase tracking-[0.2em] mb-1">
                Source
              </p>
              <p className="font-mono text-[11px] text-accent-cyan/70">{tool.source}</p>
            </div>
          )}

          {tool.url && (
            <div>
              <p className="text-[10px] font-headline font-bold text-text-secondary uppercase tracking-[0.2em] mb-1">
                URL
              </p>
              <a
                href={tool.url}
                target="_blank"
                rel="noopener noreferrer"
                className="font-mono text-[11px] text-accent-cyan hover:underline"
              >
                {tool.url}
              </a>
            </div>
          )}

          <div className="flex gap-3">
            <GlowButton
              variant="secondary"
              className="flex-1 py-2 text-[10px]"
              onClick={handleWorkbench}
              disabled={wbStatus !== "idle"}
            >
              {wbStatus === "sent" ? "SENT TO WORKBENCH" : wbStatus === "sending" ? "SENDING..." : "SEND TO WORKBENCH"}
            </GlowButton>
          </div>
        </div>
      )}
    </div>
  );
}

/**
 * ToolsRadarTab — Full tools radar view with category filter and expandable cards.
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

"use client";

import { useState, useMemo } from "react";
import { cn } from "@/lib/utils";
import type { ProjectItem } from "./types";

interface ItemsFeedProps {
  items: ProjectItem[];
  isLoading: boolean;
}

type FilterType = "all" | "method" | "tool" | "blog";

const TYPE_STYLES: Record<string, { border: string; accent: string; label: string }> = {
  method: {
    border: "border-l-purple",
    accent: "text-purple",
    label: "METHOD",
  },
  tool: {
    border: "border-l-accent-green",
    accent: "text-accent-green",
    label: "TOOL",
  },
  blog: {
    border: "border-l-accent-amber",
    accent: "text-accent-amber",
    label: "BLOG",
  },
};

/**
 * ItemsFeed — Two-column layout showing linked methods and tools for a project.
 * Filterable by type and source. Matches cockpit.html feeds section.
 */
export function ItemsFeed({ items, isLoading }: ItemsFeedProps) {
  const [filter, setFilter] = useState<FilterType>("all");

  const filtered = useMemo(() => {
    if (filter === "all") return items;
    return items.filter((item) => item.type === filter);
  }, [items, filter]);

  const methods = filtered.filter((i) => i.type === "method");
  const tools = filtered.filter((i) => i.type === "tool");
  const blogs = filtered.filter((i) => i.type === "blog");

  if (isLoading) {
    return (
      <div className="py-12 text-center">
        <div className="inline-block h-4 w-4 animate-pulse bg-accent-cyan/30" />
        <p className="mt-2 font-mono text-[10px] text-outline/50">
          LOADING_ITEMS...
        </p>
      </div>
    );
  }

  if (items.length === 0) {
    return (
      <div className="py-12 text-center">
        <p className="font-mono text-xs uppercase text-outline/50">
          No linked items found
        </p>
      </div>
    );
  }

  const filterButtons: { value: FilterType; label: string }[] = [
    { value: "all", label: "ALL" },
    { value: "method", label: "METHODS" },
    { value: "tool", label: "TOOLS" },
    { value: "blog", label: "BLOG" },
  ];

  return (
    <div className="space-y-6">
      {/* Filter bar */}
      <div className="flex gap-2">
        {filterButtons.map((btn) => (
          <button
            key={btn.value}
            onClick={() => setFilter(btn.value)}
            className={cn(
              "px-3 py-1 font-mono text-[10px] uppercase tracking-wider transition-all duration-75",
              filter === btn.value
                ? "border border-accent-cyan bg-accent-cyan/10 text-accent-cyan"
                : "border border-outline-variant/30 text-outline hover:text-accent-cyan"
            )}
          >
            {btn.label}
          </button>
        ))}
      </div>

      {/* Two-column feed */}
      <div className="grid grid-cols-1 gap-8 md:grid-cols-2">
        {/* Methods */}
        {(filter === "all" || filter === "method") && methods.length > 0 && (
          <FeedSection
            title="LINKED METHODS"
            icon="settings_input_component"
            accentClass="text-purple"
            borderClass="border-purple/30"
            items={methods}
            count={methods.length}
          />
        )}

        {/* Tools */}
        {(filter === "all" || filter === "tool") && tools.length > 0 && (
          <FeedSection
            title="LINKED TOOLS"
            icon="construction"
            accentClass="text-accent-green"
            borderClass="border-accent-green/30"
            items={tools}
            count={tools.length}
          />
        )}

        {/* Blog */}
        {(filter === "all" || filter === "blog") && blogs.length > 0 && (
          <FeedSection
            title="LINKED BLOG IDEAS"
            icon="edit_note"
            accentClass="text-accent-amber"
            borderClass="border-accent-amber/30"
            items={blogs}
            count={blogs.length}
          />
        )}
      </div>
    </div>
  );
}

// ─── Sub-components ─────────────────────────────────────────────────────────

interface FeedSectionProps {
  title: string;
  icon: string;
  accentClass: string;
  borderClass: string;
  items: ProjectItem[];
  count: number;
}

function FeedSection({
  title,
  accentClass,
  borderClass,
  items,
  count,
}: FeedSectionProps) {
  return (
    <section className="space-y-3">
      <div className={cn("flex items-center justify-between border-b pb-2", borderClass)}>
        <h2 className={cn("font-heading text-sm font-black uppercase tracking-widest", accentClass)}>
          {title}
        </h2>
        <span className="font-mono text-[10px] text-outline">
          [TOTAL: {String(count).padStart(2, "0")}]
        </span>
      </div>
      <div className="space-y-3">
        {items.map((item) => (
          <ItemCard key={item.title} item={item} />
        ))}
      </div>
    </section>
  );
}

interface ItemCardProps {
  item: ProjectItem;
}

function ItemCard({ item }: ItemCardProps) {
  const style = TYPE_STYLES[item.type] ?? TYPE_STYLES.method;

  return (
    <div
      className={cn(
        "group border-l-2 bg-bg-surface p-4 transition-colors hover:bg-surface-high",
        style.border
      )}
    >
      <div className="mb-2 flex items-start justify-between gap-2">
        <h4 className="font-heading text-xs font-bold uppercase tracking-wider text-text-primary">
          {item.title}
        </h4>
        <span className="shrink-0 font-mono text-[9px] text-outline">
          {item.discovery_source.toUpperCase()}
        </span>
      </div>

      {item.relevance_score != null && (
        <div className="flex items-center gap-4">
          <div className="h-1.5 flex-1 overflow-hidden bg-outline-variant/20">
            <div
              className={cn("h-full transition-all", style.border.replace("border-l-", "bg-"))}
              style={{ width: `${item.relevance_score}%` }}
            />
          </div>
          <span className={cn("font-mono text-[10px]", style.accent)}>
            {item.relevance_score}% MATCH
          </span>
        </div>
      )}

      {/* Hover actions */}
      <div className="mt-3 flex justify-end gap-2 opacity-0 transition-opacity group-hover:opacity-100">
        <button
          className={cn(
            "border px-2 py-1 font-mono text-[9px] uppercase transition-colors",
            `border-outline-variant/30 text-outline hover:${style.accent}`
          )}
        >
          WORKBENCH
        </button>
      </div>
    </div>
  );
}

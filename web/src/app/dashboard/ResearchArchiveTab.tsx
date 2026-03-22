"use client";

import { useState } from "react";
import { Badge } from "@/components/ui/badge";
import { useReports } from "./hooks";
import { FeedSkeleton } from "./Skeleton";
import type { ReportItem } from "./types";

type FilterType = "all" | "journalclub" | "tldr";

function ReportCard({ item }: { item: ReportItem }) {
  const borderColor =
    item.type === "journalclub" ? "border-accent-green" : "border-accent-amber";
  const badgeVariant = item.type === "journalclub" ? "journalclub" : "tldr";
  const badgeLabel = item.type === "journalclub" ? "JOURNALCLUB" : "TLDR";

  return (
    <div
      className={`bg-bg-surface p-5 border-l-4 ${borderColor} group hover:bg-surface-high/50 transition-colors`}
    >
      <div className="flex justify-between items-start mb-3">
        <h3 className="font-mono font-bold text-white group-hover:text-accent-cyan transition-colors pr-3">
          {item.title}
        </h3>
        <Badge variant={badgeVariant}>{badgeLabel}</Badge>
      </div>
      <p className="font-mono text-[11px] text-outline mb-3 italic">
        {item.date}
      </p>
      {item.highlights && item.highlights.length > 0 && (
        <ul className="space-y-2 text-sm text-text-primary">
          {item.highlights.slice(0, 3).map((h, i) => (
            <li key={i} className="flex items-start gap-2">
              <span className="mt-1.5 h-1 w-1 shrink-0 bg-accent-cyan" />
              {h}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

/**
 * ResearchArchiveTab — Full archive of JournalClub + TLDR reports with filter.
 */
export function ResearchArchiveTab() {
  const { data, isLoading } = useReports();
  const [filter, setFilter] = useState<FilterType>("all");

  const filtered = data?.filter(
    (item) => filter === "all" || item.type === filter
  );

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between border-b border-outline-variant/30 pb-2">
        <h2 className="font-headline font-bold text-lg tracking-widest text-cyan-fixed uppercase">
          Research Archive
        </h2>
        <div className="flex bg-bg-surface p-1 border border-outline-variant/30">
          {(["all", "journalclub", "tldr"] as const).map((f) => (
            <button
              key={f}
              onClick={() => setFilter(f)}
              className={`px-3 py-1 text-[10px] font-headline uppercase tracking-wider transition-colors ${
                filter === f
                  ? "bg-accent-cyan text-bg-base"
                  : "text-text-secondary hover:text-accent-cyan"
              }`}
            >
              {f === "all" ? "ALL" : f === "journalclub" ? "JOURNAL" : "TLDR"}
            </button>
          ))}
        </div>
      </div>

      <span className="font-mono text-[10px] text-outline">
        {filtered ? `${filtered.length} REPORTS` : "LOADING..."}
      </span>

      {isLoading || !filtered ? (
        <FeedSkeleton count={5} />
      ) : (
        <div className="space-y-4 max-h-[700px] overflow-y-auto pr-2">
          {filtered.map((item, i) => (
            <ReportCard key={i} item={item} />
          ))}
          {filtered.length === 0 && (
            <p className="font-mono text-sm text-text-secondary">
              No reports match the current filter
            </p>
          )}
        </div>
      )}
    </div>
  );
}

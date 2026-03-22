"use client";

import { cn } from "@/lib/utils";
import type { WorkbenchStatus } from "./types";

interface KanbanColumnProps {
  status: WorkbenchStatus;
  count: number;
  children: React.ReactNode;
}

const columnConfig: Record<
  WorkbenchStatus,
  { label: string; dotClass: string }
> = {
  queued: {
    label: "QUEUED",
    dotClass: "bg-accent-cyan",
  },
  researching: {
    label: "RESEARCHING",
    dotClass: "bg-accent-cyan animate-pulse shadow-[0_0_8px_#00F0FF]",
  },
  completed: {
    label: "COMPLETED",
    dotClass: "border border-accent-cyan bg-transparent",
  },
};

/**
 * KanbanColumn — A single column in the workbench kanban board.
 * Header with colored status dot, title, and count badge.
 */
export function KanbanColumn({ status, count, children }: KanbanColumnProps) {
  const config = columnConfig[status];

  return (
    <section className="flex flex-col gap-4">
      <div className="flex items-center justify-between border-b border-accent-cyan/20 pb-2">
        <h2
          className={cn(
            "font-heading text-lg font-bold uppercase tracking-wider text-accent-cyan",
            "flex items-center gap-2"
          )}
        >
          <span className={cn("block h-2 w-2", config.dotClass)} />
          {config.label}
        </h2>
        <span className="bg-bg-surface border border-accent-cyan/30 text-accent-cyan font-mono text-[10px] px-2 py-0.5">
          COUNT: {String(count).padStart(2, "0")}
        </span>
      </div>
      <div className="flex flex-col gap-4">{children}</div>
    </section>
  );
}

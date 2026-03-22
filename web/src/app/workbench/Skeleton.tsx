import { cn } from "@/lib/utils";

function Pulse({ className }: { className?: string }) {
  return <div className={cn("animate-pulse bg-surface-high/50", className)} />;
}

/** Skeleton for a single workbench card */
function CardSkeleton() {
  return (
    <div className="bg-bg-surface p-5 border border-accent-cyan/10">
      <div className="flex justify-between items-start mb-3">
        <Pulse className="h-4 w-16" />
      </div>
      <Pulse className="h-5 w-3/4 mb-2" />
      <div className="space-y-2 mb-5">
        <Pulse className="h-3 w-full" />
        <Pulse className="h-3 w-5/6" />
      </div>
      <Pulse className="h-9 w-full" />
    </div>
  );
}

/** Skeleton for a kanban column */
function ColumnSkeleton({ count = 2 }: { count?: number }) {
  return (
    <div className="flex flex-col gap-4">
      <div className="flex items-center justify-between border-b border-accent-cyan/20 pb-2">
        <Pulse className="h-5 w-32" />
        <Pulse className="h-4 w-16" />
      </div>
      {Array.from({ length: count }, (_, i) => (
        <CardSkeleton key={i} />
      ))}
    </div>
  );
}

/** Full workbench skeleton — 3 column grid */
export function WorkbenchSkeleton() {
  return (
    <div className="grid grid-cols-1 gap-6 items-start lg:grid-cols-3">
      <ColumnSkeleton count={3} />
      <ColumnSkeleton count={2} />
      <ColumnSkeleton count={2} />
    </div>
  );
}

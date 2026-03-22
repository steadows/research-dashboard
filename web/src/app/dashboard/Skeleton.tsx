import { cn } from "@/lib/utils";

interface SkeletonProps {
  className?: string;
}

/** Pulsing skeleton block for loading states */
export function Skeleton({ className }: SkeletonProps) {
  return (
    <div
      className={cn(
        "animate-pulse bg-surface-high/50",
        className
      )}
    />
  );
}

/** Skeleton for a single metric card */
export function MetricCardSkeleton() {
  return (
    <div className="relative bg-bg-surface p-6 border border-accent-cyan/20 box-glow-cyan flex h-32 flex-col justify-between">
      <div className="flex items-start justify-between">
        <Skeleton className="h-3 w-24" />
        <Skeleton className="h-2 w-16" />
      </div>
      <div className="flex items-baseline gap-2">
        <Skeleton className="h-10 w-16" />
        <Skeleton className="h-3 w-12" />
      </div>
    </div>
  );
}

/** 4x metric card skeleton row */
export function MetricCardsSkeleton() {
  return (
    <section className="grid grid-cols-1 gap-6 sm:grid-cols-2 lg:grid-cols-4">
      <MetricCardSkeleton />
      <MetricCardSkeleton />
      <MetricCardSkeleton />
      <MetricCardSkeleton />
    </section>
  );
}

/** Skeleton for a feed card (research, blog, tool) */
export function FeedCardSkeleton() {
  return (
    <div className="bg-bg-surface p-5 border-l-4 border-accent-cyan/20">
      <div className="flex justify-between items-start mb-3">
        <Skeleton className="h-5 w-3/4" />
        <Skeleton className="h-4 w-20" />
      </div>
      <Skeleton className="h-3 w-32 mb-3" />
      <div className="space-y-2">
        <Skeleton className="h-3 w-full" />
        <Skeleton className="h-3 w-5/6" />
      </div>
    </div>
  );
}

/** Skeleton for a list of feed cards */
export function FeedSkeleton({ count = 3 }: { count?: number }) {
  return (
    <div className="space-y-4">
      {Array.from({ length: count }, (_, i) => (
        <FeedCardSkeleton key={i} />
      ))}
    </div>
  );
}

/** Skeleton for the tools radar sidebar list */
export function ToolsListSkeleton({ count = 5 }: { count?: number }) {
  return (
    <div className="space-y-4">
      {Array.from({ length: count }, (_, i) => (
        <div key={i} className="flex items-center justify-between p-2">
          <div className="flex items-center gap-3">
            <Skeleton className="h-1.5 w-1.5 rounded-full" />
            <Skeleton className="h-4 w-28" />
          </div>
          <Skeleton className="h-4 w-16" />
        </div>
      ))}
    </div>
  );
}

/** Skeleton for the agentic hub cards */
export function AgenticCardSkeleton() {
  return (
    <div className="bg-bg-surface border-l-4 border-indigo/20 p-5 flex flex-col gap-5">
      <div className="space-y-2">
        <Skeleton className="h-6 w-3/4" />
        <Skeleton className="h-3 w-40" />
      </div>
      <div className="space-y-2">
        <Skeleton className="h-3 w-24" />
        <Skeleton className="h-3 w-full" />
        <Skeleton className="h-3 w-5/6" />
        <Skeleton className="h-3 w-4/6" />
      </div>
      <div className="space-y-2">
        <Skeleton className="h-3 w-32" />
        <Skeleton className="h-16 w-full" />
      </div>
      <div className="flex gap-2">
        <Skeleton className="h-5 w-12" />
        <Skeleton className="h-5 w-16" />
      </div>
      <div className="flex gap-3 mt-auto">
        <Skeleton className="h-9 flex-1" />
        <Skeleton className="h-9 flex-1" />
      </div>
    </div>
  );
}

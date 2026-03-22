import { HUDCard } from "./hud-card";
import { cn } from "@/lib/utils";

interface MetricCardProps {
  /** Index label like "[01]" */
  index: string;
  /** Metric title */
  title: string;
  /** Large numeric value */
  value: string | number;
  /** Delta or status text next to value */
  delta?: string;
  /** Color for delta text */
  deltaColor?: "cyan" | "green" | "amber" | "red";
  /** Additional info in top-right */
  meta?: string;
  /** Additional classes */
  className?: string;
}

const deltaColorMap = {
  cyan: "text-accent-cyan",
  green: "text-accent-green",
  amber: "text-accent-amber",
  red: "text-accent-red",
} as const;

/**
 * MetricCard — HUD metric display card with large value and delta.
 */
export function MetricCard({
  index,
  title,
  value,
  delta,
  deltaColor = "green",
  meta,
  className,
}: MetricCardProps) {
  return (
    <HUDCard
      index={index}
      title={title}
      meta={meta}
      className={cn("flex h-32 flex-col justify-between", className)}
    >
      <div className="flex items-baseline gap-2">
        <span className="font-mono text-4xl font-bold text-white">{value}</span>
        {delta && (
          <span className={cn("font-mono text-[10px]", deltaColorMap[deltaColor])}>
            {delta}
          </span>
        )}
      </div>
    </HUDCard>
  );
}

import { cn } from "@/lib/utils";

interface DataReadoutProps {
  /** Label above the value */
  label: string;
  /** The data value to display */
  value: string | number;
  /** Unit or suffix after the value */
  unit?: string;
  /** Accent color for the value */
  color?: "cyan" | "green" | "amber" | "red" | "white";
  /** Additional classes */
  className?: string;
}

const colorMap = {
  cyan: "text-accent-cyan",
  green: "text-accent-green",
  amber: "text-accent-amber",
  red: "text-accent-red",
  white: "text-white",
} as const;

/**
 * DataReadout — Monospace data display for numeric/telemetry values.
 * Uses JetBrains Mono to prevent number jumping.
 */
export function DataReadout({
  label,
  value,
  unit,
  color = "cyan",
  className,
}: DataReadoutProps) {
  return (
    <div className={cn("flex flex-col gap-1", className)}>
      <span className="font-headline text-[9px] uppercase tracking-[0.2em] text-text-secondary">
        {label}
      </span>
      <span className={cn("font-mono text-lg font-bold", colorMap[color])}>
        {value}
        {unit && (
          <span className="ml-1 text-xs font-normal text-text-muted">{unit}</span>
        )}
      </span>
    </div>
  );
}

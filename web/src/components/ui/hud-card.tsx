import { cn } from "@/lib/utils";

interface HUDCardProps {
  children: React.ReactNode;
  /** Index label like "[01]" */
  index?: string;
  /** Card title */
  title?: string;
  /** Additional info in top-right corner */
  meta?: string;
  /** Additional classes */
  className?: string;
}

/**
 * HUDCard — Metric card with glow border.
 * 0px border-radius, glow (not shadow), no corner brackets.
 */
export function HUDCard({
  children,
  index,
  title,
  meta,
  className,
}: HUDCardProps) {
  return (
    <div
      className={cn(
        "relative bg-bg-surface p-6 border border-accent-cyan/20 box-glow-cyan transition-shadow duration-200 hover:box-glow-cyan-lg hover:border-accent-cyan/40",
        className
      )}
    >
      {(index || title || meta) && (
        <div className="mb-4 flex items-start justify-between">
          <span className="font-headline text-xs uppercase tracking-[0.2em] text-accent-cyan/70">
            {index && `${index} `}{title}
          </span>
          {meta && (
            <span className="font-mono text-[9px] text-accent-cyan/40">
              {meta}
            </span>
          )}
        </div>
      )}

      {children}
    </div>
  );
}

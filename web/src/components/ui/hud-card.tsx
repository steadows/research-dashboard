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
 * HUDCard — Metric card with corner brackets and glow border.
 * 0px border-radius, glow (not shadow), corner bracket accents.
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
        "relative bg-bg-surface p-6 border border-accent-cyan/20 box-glow-cyan",
        className
      )}
    >
      {/* Corner brackets */}
      <div className="pointer-events-none absolute -left-px -top-px h-3 w-3 border-l-2 border-t-2 border-cyan-fixed" aria-hidden="true" />
      <div className="pointer-events-none absolute -right-px -top-px h-3 w-3 border-r-2 border-t-2 border-cyan-fixed" aria-hidden="true" />
      <div className="pointer-events-none absolute -bottom-px -left-px h-3 w-3 border-b-2 border-l-2 border-cyan-fixed" aria-hidden="true" />
      <div className="pointer-events-none absolute -bottom-px -right-px h-3 w-3 border-b-2 border-r-2 border-cyan-fixed" aria-hidden="true" />

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

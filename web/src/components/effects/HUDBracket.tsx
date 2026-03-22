"use client";

import { cn } from "@/lib/utils";

type AccentColor = "cyan" | "green" | "amber" | "red";

interface HUDBracketProps {
  children: React.ReactNode;
  /** Optional label displayed at the top-left of the frame (monospace, uppercase) */
  label?: string;
  /** Optional status text displayed at the top-right */
  status?: string;
  /** Accent color for bracket lines and label */
  accentColor?: AccentColor;
  /** Length of the corner bracket arms (px) — defaults to 20 */
  cornerSize?: number;
  /** Thickness of bracket lines (px) — defaults to 1 */
  lineWidth?: number;
  /** Whether corners animate with a subtle glow pulse */
  animated?: boolean;
  /** Additional classes for the outer wrapper */
  className?: string;
  /** Additional classes for the inner content area */
  contentClassName?: string;
  /** Show corner bracket lines and dots — defaults to true */
  corners?: boolean;
}

const colorMap: Record<AccentColor, {
  border: string;
  text: string;
  glow: string;
  dotBg: string;
}> = {
  cyan: {
    border: "border-accent-cyan/40",
    text: "text-accent-cyan",
    glow: "drop-glow-cyan",
    dotBg: "bg-accent-cyan",
  },
  green: {
    border: "border-accent-green/40",
    text: "text-accent-green",
    glow: "drop-glow-green",
    dotBg: "bg-accent-green",
  },
  amber: {
    border: "border-accent-amber/40",
    text: "text-accent-amber",
    glow: "drop-glow-amber",
    dotBg: "bg-accent-amber",
  },
  red: {
    border: "border-accent-red/40",
    text: "text-accent-red",
    glow: "drop-glow-red",
    dotBg: "bg-accent-red",
  },
};

/**
 * HUDBracket — Decorative HUD-style frame for wrapping sections.
 *
 * Renders tactical corner brackets with optional label, status indicator,
 * and animated glow. Purely decorative — content is passed as children.
 *
 * @example
 * ```tsx
 * <HUDBracket label="TECH ARSENAL" accentColor="cyan" animated>
 *   <SkillsGrid />
 * </HUDBracket>
 * ```
 */
export function HUDBracket({
  children,
  label,
  status,
  accentColor = "cyan",
  cornerSize = 20,
  lineWidth = 1,
  animated = false,
  className,
  contentClassName,
  corners = true,
}: HUDBracketProps) {
  const colors = colorMap[accentColor];

  const cornerStyle = {
    width: `${cornerSize}px`,
    height: `${cornerSize}px`,
    borderWidth: `${lineWidth}px`,
  };

  return (
    <div
      className={cn(
        "relative",
        animated && "motion-safe:animate-glow-pulse",
        className
      )}
    >
      {corners && (
        <>
          {/* ── Top-left corner ── */}
          <div
            className={cn(
              "pointer-events-none absolute top-0 left-0 border-t border-l",
              colors.border,
              animated && colors.glow
            )}
            style={cornerStyle}
            aria-hidden="true"
          />

          {/* ── Top-right corner ── */}
          <div
            className={cn(
              "pointer-events-none absolute top-0 right-0 border-t border-r",
              colors.border,
              animated && colors.glow
            )}
            style={cornerStyle}
            aria-hidden="true"
          />

          {/* ── Bottom-left corner ── */}
          <div
            className={cn(
              "pointer-events-none absolute bottom-0 left-0 border-b border-l",
              colors.border,
              animated && colors.glow
            )}
            style={cornerStyle}
            aria-hidden="true"
          />

          {/* ── Bottom-right corner ── */}
          <div
            className={cn(
              "pointer-events-none absolute right-0 bottom-0 border-b border-r",
              colors.border,
              animated && colors.glow
            )}
            style={cornerStyle}
            aria-hidden="true"
          />

          {/* ── Corner dots (decorative pips) ── */}
          <div
            className={cn(
              "pointer-events-none absolute top-0 left-0 -translate-x-[1px] -translate-y-[1px] h-[3px] w-[3px] rounded-full",
              colors.dotBg,
              "opacity-60"
            )}
            aria-hidden="true"
          />
          <div
            className={cn(
              "pointer-events-none absolute top-0 right-0 translate-x-[1px] -translate-y-[1px] h-[3px] w-[3px] rounded-full",
              colors.dotBg,
              "opacity-60"
            )}
            aria-hidden="true"
          />
          <div
            className={cn(
              "pointer-events-none absolute bottom-0 left-0 -translate-x-[1px] translate-y-[1px] h-[3px] w-[3px] rounded-full",
              colors.dotBg,
              "opacity-60"
            )}
            aria-hidden="true"
          />
          <div
            className={cn(
              "pointer-events-none absolute right-0 bottom-0 translate-x-[1px] translate-y-[1px] h-[3px] w-[3px] rounded-full",
              colors.dotBg,
              "opacity-60"
            )}
            aria-hidden="true"
          />
        </>
      )}

      {/* ── Top bar: label + status ── */}
      {(label || status) && (
        <div
          className="pointer-events-none absolute top-0 right-0 left-0 flex items-center justify-between px-6 -translate-y-1/2"
          aria-hidden="true"
        >
          {label ? (
            <span
              className={cn(
                "font-heading text-[10px] uppercase tracking-[0.25em] leading-none",
                "bg-bg-base px-2",
                colors.text,
                animated && colors.glow
              )}
            >
              [ {label} ]
            </span>
          ) : (
            <span />
          )}
          {status && (
            <span className="flex items-center gap-1.5 bg-bg-base px-2">
              <span
                className={cn(
                  "inline-block h-1.5 w-1.5 rounded-full",
                  colors.dotBg,
                  animated && "motion-safe:animate-glow-pulse"
                )}
              />
              <span
                className={cn(
                  "font-heading text-[9px] uppercase tracking-[0.2em] leading-none",
                  colors.text,
                  "opacity-60"
                )}
              >
                {status}
              </span>
            </span>
          )}
        </div>
      )}

      {/* ── Content ── */}
      <div className={cn("relative p-6", contentClassName)}>
        {children}
      </div>
    </div>
  );
}

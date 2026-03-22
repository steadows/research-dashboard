"use client";

import { cn } from "@/lib/utils";

interface GlitchTextProps {
  children: string;
  as?: "h1" | "h2" | "h3" | "h4" | "span" | "p";
  className?: string;
  glowColor?: "cyan" | "green" | "amber" | "red";
  continuous?: boolean;
}

const glowMap = {
  cyan: "text-glow-cyan",
  green: "text-glow-green",
  amber: "text-glow-amber",
  red: "text-glow-red",
} as const;

export function GlitchText({
  children,
  as: Tag = "span",
  className,
  glowColor = "cyan",
  continuous = false,
}: GlitchTextProps) {
  return (
    <Tag
      className={cn(
        "glitch-wrapper relative inline-block",
        glowMap[glowColor],
        className
      )}
      data-text={children}
      data-continuous={continuous ? "" : undefined}
    >
      {children}
      <span
        className="glitch-layer glitch-layer--before pointer-events-none absolute inset-0 select-none"
        aria-hidden="true"
        data-text={children}
      />
      <span
        className="glitch-layer glitch-layer--after pointer-events-none absolute inset-0 select-none"
        aria-hidden="true"
        data-text={children}
      />
    </Tag>
  );
}

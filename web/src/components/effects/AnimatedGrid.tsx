"use client";

import { cn } from "@/lib/utils";

interface AnimatedGridProps {
  className?: string;
}

export function AnimatedGrid({ className }: AnimatedGridProps) {
  return (
    <div
      className={cn("pointer-events-none fixed inset-0 overflow-hidden", className)}
      aria-hidden="true"
    >
      {/* Perspective grid floor */}
      <div className="absolute inset-0 grid-perspective" />

      {/* Flat overlay grid for depth */}
      <div className="absolute inset-0 grid-overlay opacity-[0.03]" />

      {/* Subtle radial gradient to fade edges */}
      <div className="absolute inset-0 bg-[radial-gradient(ellipse_at_center,transparent_0%,var(--color-bg-base)_70%)]" />
    </div>
  );
}

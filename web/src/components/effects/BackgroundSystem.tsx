"use client";

import { AnimatedGrid } from "@/components/effects/AnimatedGrid";
import { FloatingParticles } from "@/components/effects/FloatingParticles";

export function BackgroundSystem() {
  return (
    <div className="pointer-events-none fixed inset-0 z-0" aria-hidden="true">
      <AnimatedGrid />
      <FloatingParticles particleCount={40} />
    </div>
  );
}

"use client";

import { LazyMotion, domAnimation } from "framer-motion";

/**
 * Single root-level LazyMotion provider.
 * All `m` components in the tree inherit this context —
 * no per-component LazyMotion wrappers needed.
 */
export function MotionProvider({ children }: { children: React.ReactNode }) {
  return <LazyMotion features={domAnimation}>{children}</LazyMotion>;
}

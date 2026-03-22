"use client";

import { m, useScroll, useTransform, useReducedMotion } from "framer-motion";
import { cn } from "@/lib/utils";

// ── Component ──

interface ScrollIndicatorProps {
  /** ID of the element to scroll to on click (without #) */
  targetId?: string;
  className?: string;
}

export function ScrollIndicator({
  targetId,
  className,
}: ScrollIndicatorProps) {
  const prefersReducedMotion = useReducedMotion();

  // Fade out as user scrolls down (GPU-accelerated: opacity only)
  const { scrollY } = useScroll();
  const scrollOpacity = useTransform(scrollY, [0, 200], [1, 0]);

  const handleClick = () => {
    if (targetId) {
      const el = document.getElementById(targetId);
      if (el) {
        el.scrollIntoView({ behavior: "smooth" });
        return;
      }
    }
    // Fallback: scroll down one viewport height
    window.scrollTo({ top: window.innerHeight, behavior: "smooth" });
  };

  return (
    <m.button
      initial={{ opacity: 0, y: -10 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: 2.5, duration: 0.6, ease: "easeOut" }}
      style={{ opacity: prefersReducedMotion ? 1 : scrollOpacity }}
      onClick={handleClick}
      aria-label="Scroll down"
      className={cn(
        "absolute bottom-8 left-1/2 -translate-x-1/2 z-20",
        "flex flex-col items-center gap-3 cursor-pointer",
        "group focus:outline-none",
        className
      )}
    >
      {/* Label */}
      <span className="font-heading text-[9px] tracking-[0.3em] text-text-muted/60 transition-colors duration-300 group-hover:text-accent-cyan/80">
        SCROLL
      </span>

      {/* Radar ping + chevron container */}
      <div className="relative flex items-center justify-center">
        {/* Radar ping rings (CSS-animated for performance) */}
        {!prefersReducedMotion && (
          <div className="absolute inset-0 flex items-center justify-center" aria-hidden="true">
            <span className="absolute h-8 w-8 rounded-full border border-accent-cyan/30 motion-safe:animate-radar-ping" />
            <span
              className="absolute h-8 w-8 rounded-full border border-accent-cyan/20 motion-safe:animate-radar-ping"
              style={{ animationDelay: "1s" }}
            />
          </div>
        )}

        {/* Chevron arrows — continuous bounce via CSS for performance */}
        <div className={cn(
          "relative flex flex-col items-center gap-0.5",
          !prefersReducedMotion && "motion-safe:animate-scroll-bounce"
        )}>
          <svg
            width="20"
            height="10"
            viewBox="0 0 20 10"
            fill="none"
            className="text-accent-cyan/50 transition-colors duration-300 group-hover:text-accent-cyan drop-glow-cyan"
          >
            <path
              d="M2 2L10 8L18 2"
              stroke="currentColor"
              strokeWidth="1.5"
              strokeLinecap="round"
              strokeLinejoin="round"
            />
          </svg>
          <svg
            width="20"
            height="10"
            viewBox="0 0 20 10"
            fill="none"
            className="text-accent-cyan/30 transition-colors duration-300 group-hover:text-accent-cyan/70"
          >
            <path
              d="M2 2L10 8L18 2"
              stroke="currentColor"
              strokeWidth="1.5"
              strokeLinecap="round"
              strokeLinejoin="round"
            />
          </svg>
        </div>
      </div>
    </m.button>
  );
}

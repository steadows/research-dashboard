"use client";

import { createContext, useContext, useRef } from "react";
import {
  m,
  useInView,
  useReducedMotion,
  type Variants,
  type UseInViewOptions,
} from "framer-motion";
import { cn } from "@/lib/utils";

type ViewportMargin = UseInViewOptions["margin"];

// ─── Animation Types ─────────────────────────────────────────────────────────

type RevealAnimation =
  | "fadeUp"
  | "fadeDown"
  | "fadeIn"
  | "slideLeft"
  | "slideRight"
  | "scaleUp";

// ─── Variants (defined OUTSIDE components to prevent re-renders) ─────────────

const revealVariants: Record<RevealAnimation, Variants> = {
  fadeUp: {
    hidden: { opacity: 0, y: 40 },
    visible: { opacity: 1, y: 0 },
  },
  fadeDown: {
    hidden: { opacity: 0, y: -40 },
    visible: { opacity: 1, y: 0 },
  },
  fadeIn: {
    hidden: { opacity: 0 },
    visible: { opacity: 1 },
  },
  slideLeft: {
    hidden: { opacity: 0, x: -60 },
    visible: { opacity: 1, x: 0 },
  },
  slideRight: {
    hidden: { opacity: 0, x: 60 },
    visible: { opacity: 1, x: 0 },
  },
  scaleUp: {
    hidden: { opacity: 0, scale: 0.85 },
    visible: { opacity: 1, scale: 1 },
  },
};

/** Reduced-motion fallback — instant opacity with no spatial movement */
const reducedMotionVariants: Variants = {
  hidden: { opacity: 0 },
  visible: { opacity: 1 },
};

// ─── Context for stagger groups ──────────────────────────────────────────────

interface RevealGroupContext {
  animation: RevealAnimation;
  duration: number;
  shouldReduceMotion: boolean | null;
}

const RevealGroupCtx = createContext<RevealGroupContext | null>(null);

// ─── Prop Types ──────────────────────────────────────────────────────────────

interface SectionRevealProps {
  children: React.ReactNode;
  /** Animation style — defaults to "fadeUp" */
  animation?: RevealAnimation;
  /** Delay before animation starts (seconds) — defaults to 0 */
  delay?: number;
  /** Animation duration (seconds) — defaults to 0.6 */
  duration?: number;
  /** Only animate once when entering viewport — defaults to true */
  once?: boolean;
  /** IntersectionObserver margin — negative values trigger earlier */
  viewportMargin?: ViewportMargin;
  /** Fraction of element visible before triggering (0–1) — defaults to 0.2 */
  threshold?: number;
  /** Additional CSS classes */
  className?: string;
}

interface SectionRevealGroupProps {
  children: React.ReactNode;
  /** Animation applied to each child item — defaults to "fadeUp" */
  animation?: RevealAnimation;
  /** Delay between each child's reveal (seconds) — defaults to 0.1 */
  staggerDelay?: number;
  /** Duration for each child animation (seconds) — defaults to 0.5 */
  duration?: number;
  /** Initial delay before the first child animates (seconds) — defaults to 0.15 */
  delayChildren?: number;
  /** Only animate once when entering viewport — defaults to true */
  once?: boolean;
  /** IntersectionObserver margin */
  viewportMargin?: ViewportMargin;
  /** Fraction of element visible before triggering (0–1) — defaults to 0.15 */
  threshold?: number;
  /** Additional CSS classes for the container */
  className?: string;
}

interface SectionRevealItemProps {
  children: React.ReactNode;
  /** Override the group's animation for this specific item */
  animation?: RevealAnimation;
  /** Additional CSS classes */
  className?: string;
}

// ─── Components ──────────────────────────────────────────────────────────────

/**
 * SectionReveal — Scroll-triggered reveal animation wrapper.
 *
 * Wraps a section or element and reveals it with a Framer Motion animation
 * when it scrolls into the viewport. Uses GPU-accelerated properties only
 * (opacity, transform) and respects `prefers-reduced-motion`.
 *
 * @example
 * ```tsx
 * <SectionReveal animation="fadeUp" delay={0.2}>
 *   <h2>TECH ARSENAL</h2>
 *   <p>Skills and tools...</p>
 * </SectionReveal>
 * ```
 */
export function SectionReveal({
  children,
  animation = "fadeUp",
  delay = 0,
  duration = 0.6,
  once = true,
  viewportMargin = "-80px",
  threshold = 0.2,
  className,
}: SectionRevealProps) {
  const ref = useRef<HTMLDivElement>(null);
  const isInView = useInView(ref, {
    once,
    margin: viewportMargin,
    amount: threshold,
  });
  const shouldReduceMotion = useReducedMotion();

  const activeVariants = shouldReduceMotion
    ? reducedMotionVariants
    : revealVariants[animation];

  return (
    <m.div
      ref={ref}
      variants={activeVariants}
      initial="hidden"
      animate={isInView ? "visible" : "hidden"}
      transition={{
        duration: shouldReduceMotion ? 0 : duration,
        delay: shouldReduceMotion ? 0 : delay,
        ease: [0.25, 0.1, 0.25, 1],
      }}
      className={cn(className)}
    >
      {children}
    </m.div>
  );
}

/**
 * SectionRevealGroup — Staggered scroll-triggered reveal for multiple children.
 *
 * Each direct child wrapped in `<SectionRevealItem>` will animate in sequence
 * with a configurable stagger delay. The group controls orchestration timing;
 * items inherit the animation style via context.
 *
 * @example
 * ```tsx
 * <SectionRevealGroup animation="fadeUp" staggerDelay={0.1}>
 *   <SectionRevealItem>
 *     <SkillCard title="Python" />
 *   </SectionRevealItem>
 *   <SectionRevealItem>
 *     <SkillCard title="TensorFlow" />
 *   </SectionRevealItem>
 * </SectionRevealGroup>
 * ```
 */
export function SectionRevealGroup({
  children,
  animation = "fadeUp",
  staggerDelay = 0.1,
  duration = 0.5,
  delayChildren = 0.15,
  once = true,
  viewportMargin = "-60px",
  threshold = 0.15,
  className,
}: SectionRevealGroupProps) {
  const ref = useRef<HTMLDivElement>(null);
  const isInView = useInView(ref, {
    once,
    margin: viewportMargin,
    amount: threshold,
  });
  const shouldReduceMotion = useReducedMotion();

  const containerVariants: Variants = {
    hidden: {},
    visible: {
      transition: {
        staggerChildren: shouldReduceMotion ? 0 : staggerDelay,
        delayChildren: shouldReduceMotion ? 0 : delayChildren,
      },
    },
  };

  return (
    <RevealGroupCtx.Provider
      value={{ animation, duration, shouldReduceMotion }}
    >
      <m.div
        ref={ref}
        variants={containerVariants}
        initial="hidden"
        animate={isInView ? "visible" : "hidden"}
        className={cn(className)}
      >
        {children}
      </m.div>
    </RevealGroupCtx.Provider>
  );
}

/**
 * SectionRevealItem — Individual item within a `<SectionRevealGroup>`.
 *
 * Inherits animation style and timing from the parent group via context.
 * Can optionally override the animation for this specific item.
 * Must be a direct motion child of `SectionRevealGroup`.
 *
 * @example
 * ```tsx
 * <SectionRevealItem className="col-span-1">
 *   <ProjectCard project={project} />
 * </SectionRevealItem>
 * ```
 */
export function SectionRevealItem({
  children,
  animation,
  className,
}: SectionRevealItemProps) {
  const groupCtx = useContext(RevealGroupCtx);

  const resolvedAnimation = animation ?? groupCtx?.animation ?? "fadeUp";
  const resolvedDuration = groupCtx?.duration ?? 0.5;
  const shouldReduceMotion = groupCtx?.shouldReduceMotion ?? false;

  const baseVariants = shouldReduceMotion
    ? reducedMotionVariants
    : revealVariants[resolvedAnimation];

  // Merge transition config into the visible variant
  const itemVariants: Variants = {
    hidden: baseVariants.hidden,
    visible: {
      ...baseVariants.visible,
      transition: {
        duration: shouldReduceMotion ? 0 : resolvedDuration,
        ease: [0.25, 0.1, 0.25, 1],
      },
    },
  };

  return (
    <m.div variants={itemVariants} className={cn(className)}>
      {children}
    </m.div>
  );
}

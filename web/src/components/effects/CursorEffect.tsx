"use client";

import { useEffect, useState } from "react";
import { motion, useMotionValue, useSpring } from "framer-motion";

/**
 * Custom cursor effect — desktop only.
 * Renders a snappy center dot and a trailing glow ring with spring physics.
 * Scales up when hovering interactive elements.
 * Shrinks on click for tactile feedback.
 * Respects `prefers-reduced-motion` and skips on touch devices.
 *
 * Visibility logic:
 * - Starts hidden (opacity 0, position off-screen)
 * - `mousemove` makes it visible + updates position (always reliable)
 * - `mouseleave` on <html> hides it when the mouse leaves the viewport
 * - No `mouseenter` needed — `mousemove` handles everything
 */
export function CursorEffect() {
  const [isActive, setIsActive] = useState(false);

  // ── Direct mouse position (no spring — snappy dot) ──
  const cursorX = useMotionValue(-100);
  const cursorY = useMotionValue(-100);

  // ── Spring-delayed position (trailing glow ring) ──
  const ringSpring = { damping: 25, stiffness: 200, mass: 0.5 };
  const ringX = useSpring(cursorX, ringSpring);
  const ringY = useSpring(cursorY, ringSpring);

  // ── Opacity (instant — no spring, cursors should never fade) ──
  const cursorOpacity = useMotionValue(0);

  // ── Ring scale (grows on interactive element hover) ──
  const ringScale = useMotionValue(1);
  const smoothRingScale = useSpring(ringScale, { damping: 20, stiffness: 300 });

  // ── Dot scale (shrinks on click) ──
  const dotScale = useMotionValue(1);
  const smoothDotScale = useSpring(dotScale, { damping: 20, stiffness: 400 });

  useEffect(() => {
    // Gate: touch devices or reduced-motion preference
    const isTouch = window.matchMedia("(pointer: coarse)").matches;
    const reducedMotion = window.matchMedia(
      "(prefers-reduced-motion: reduce)"
    ).matches;

    if (isTouch || reducedMotion) return;

    setIsActive(true);
    document.documentElement.classList.add("cursor-effect-active");

    const handleMouseMove = (e: MouseEvent) => {
      cursorX.set(e.clientX);
      cursorY.set(e.clientY);

      // Always ensure visibility — mousemove is the single source of truth
      cursorOpacity.set(1);

      // Detect interactive elements for scale-up effect
      const target = e.target as HTMLElement;
      const isInteractive = target.closest(
        "a, button, [data-magnetic], input, textarea, select, [role='button']"
      );
      ringScale.set(isInteractive ? 2 : 1);
    };

    // Hide cursor when mouse leaves the viewport entirely
    const handleMouseLeave = () => cursorOpacity.set(0);

    const handleMouseDown = () => dotScale.set(0.6);
    const handleMouseUp = () => dotScale.set(1);

    window.addEventListener("mousemove", handleMouseMove);
    document.documentElement.addEventListener("mouseleave", handleMouseLeave);
    window.addEventListener("mousedown", handleMouseDown);
    window.addEventListener("mouseup", handleMouseUp);

    return () => {
      window.removeEventListener("mousemove", handleMouseMove);
      document.documentElement.removeEventListener("mouseleave", handleMouseLeave);
      window.removeEventListener("mousedown", handleMouseDown);
      window.removeEventListener("mouseup", handleMouseUp);
      document.documentElement.classList.remove("cursor-effect-active");
    };
  }, [cursorX, cursorY, cursorOpacity, ringScale, dotScale]);

  // Don't render on touch / reduced-motion
  if (!isActive) return null;

  return (
    <>
      {/* Glow trail ring — follows with spring delay */}
      <motion.div
        className="pointer-events-none fixed left-0 top-0 z-[9999] h-10 w-10 rounded-full border border-accent-cyan/30"
        style={{
          x: ringX,
          y: ringY,
          translateX: "-50%",
          translateY: "-50%",
          opacity: cursorOpacity,
          scale: smoothRingScale,
          boxShadow:
            "0 0 15px rgba(0, 240, 255, 0.15), 0 0 40px rgba(0, 240, 255, 0.06)",
        }}
        aria-hidden="true"
      />

      {/* Center dot — follows cursor exactly */}
      <motion.div
        className="pointer-events-none fixed left-0 top-0 z-[9999] h-2.5 w-2.5 rounded-full bg-accent-cyan"
        style={{
          x: cursorX,
          y: cursorY,
          translateX: "-50%",
          translateY: "-50%",
          opacity: cursorOpacity,
          scale: smoothDotScale,
          boxShadow:
            "0 0 8px rgba(0, 240, 255, 0.8), 0 0 20px rgba(0, 240, 255, 0.3)",
        }}
        aria-hidden="true"
      />
    </>
  );
}

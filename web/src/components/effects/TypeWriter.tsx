"use client";

import { useState, useEffect, useRef } from "react";
import { cn } from "@/lib/utils";

interface TypeWriterProps {
  /** Single string or array of strings to cycle through */
  strings: string | string[];
  /** Typing speed in ms per character */
  speed?: number;
  /** Deletion speed in ms per character */
  deleteSpeed?: number;
  /** Pause duration (ms) after typing a string before deleting */
  pauseTime?: number;
  /** Pause duration (ms) after deleting before typing next string */
  pauseBeforeType?: number;
  /** Loop through strings continuously — defaults to true when multiple strings */
  loop?: boolean;
  /** Cursor character */
  cursor?: string;
  /** Cursor glow color accent */
  cursorColor?: "cyan" | "green" | "amber" | "red";
  /** Show the blinking cursor — defaults to true */
  showCursor?: boolean;
  /** Delay (ms) before typing starts */
  startDelay?: number;
  /** Wrapper element type */
  as?: "span" | "p" | "h1" | "h2" | "h3" | "h4" | "div";
  /** Additional classes for the wrapper */
  className?: string;
  /** Additional classes for the cursor */
  cursorClassName?: string;
  /** Callback fired when all strings have been typed (only when loop=false) */
  onComplete?: () => void;
}

const cursorGlowMap = {
  cyan: "text-accent-cyan text-glow-cyan",
  green: "text-accent-green text-glow-green",
  amber: "text-accent-amber text-glow-amber",
  red: "text-accent-red text-glow-red",
} as const;

export function TypeWriter({
  strings,
  speed = 50,
  deleteSpeed = 30,
  pauseTime = 1500,
  pauseBeforeType = 500,
  loop = true,
  cursor = "\u2588",
  cursorColor = "cyan",
  showCursor = true,
  startDelay = 0,
  as: Tag = "span",
  className,
  cursorClassName,
  onComplete,
}: TypeWriterProps) {
  const normalizedStrings = Array.isArray(strings) ? strings : [strings];
  const shouldLoop = normalizedStrings.length > 1 ? loop : false;

  const [displayText, setDisplayText] = useState("");
  const [isDone, setIsDone] = useState(false);

  // Use refs for mutable engine state to avoid stale closures
  const phaseRef = useRef<"idle" | "typing" | "pausing" | "deleting" | "waiting" | "done">("idle");
  const charIndexRef = useRef(0);
  const stringIndexRef = useRef(0);
  const timeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(() => {
    // Check prefers-reduced-motion
    const mql = window.matchMedia("(prefers-reduced-motion: reduce)");
    if (mql.matches) {
      setDisplayText(normalizedStrings[0]);
      setIsDone(true);
      return;
    }

    const clear = () => {
      if (timeoutRef.current) clearTimeout(timeoutRef.current);
    };

    const tick = () => {
      const phase = phaseRef.current;
      const si = stringIndexRef.current;
      const currentString = normalizedStrings[si];
      const isLastString = si === normalizedStrings.length - 1;

      if (phase === "typing") {
        if (charIndexRef.current < currentString.length) {
          charIndexRef.current += 1;
          setDisplayText(currentString.slice(0, charIndexRef.current));
          timeoutRef.current = setTimeout(tick, speed);
        } else {
          // Finished typing
          if (shouldLoop || !isLastString) {
            phaseRef.current = "pausing";
            timeoutRef.current = setTimeout(tick, pauseTime);
          } else {
            phaseRef.current = "done";
            setIsDone(true);
            onComplete?.();
          }
        }
      } else if (phase === "pausing") {
        phaseRef.current = "deleting";
        timeoutRef.current = setTimeout(tick, deleteSpeed);
      } else if (phase === "deleting") {
        if (charIndexRef.current > 0) {
          charIndexRef.current -= 1;
          setDisplayText(currentString.slice(0, charIndexRef.current));
          timeoutRef.current = setTimeout(tick, deleteSpeed);
        } else {
          // Move to next string
          const nextIndex = shouldLoop
            ? (si + 1) % normalizedStrings.length
            : si + 1;

          if (nextIndex < normalizedStrings.length || shouldLoop) {
            stringIndexRef.current = nextIndex % normalizedStrings.length;
            phaseRef.current = "waiting";
            timeoutRef.current = setTimeout(tick, pauseBeforeType);
          } else {
            phaseRef.current = "done";
            setIsDone(true);
            onComplete?.();
          }
        }
      } else if (phase === "waiting") {
        charIndexRef.current = 0;
        phaseRef.current = "typing";
        timeoutRef.current = setTimeout(tick, speed);
      }
    };

    // Start the engine after delay
    timeoutRef.current = setTimeout(() => {
      phaseRef.current = "typing";
      charIndexRef.current = 0;
      stringIndexRef.current = 0;
      tick();
    }, startDelay);

    return clear;
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  return (
    <Tag
      className={cn("font-heading", className)}
      aria-label={normalizedStrings.join(", ")}
    >
      <span aria-hidden="true">{displayText}</span>
      {showCursor && (
        <span
          className={cn(
            "ml-[1px] inline-block animate-typing-cursor",
            cursorGlowMap[cursorColor],
            cursorClassName
          )}
          aria-hidden="true"
        >
          {cursor}
        </span>
      )}
      {/* Screen reader accessible text */}
      <span className="sr-only">{normalizedStrings.join(", ")}</span>
    </Tag>
  );
}

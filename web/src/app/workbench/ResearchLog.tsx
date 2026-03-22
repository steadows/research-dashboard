"use client";

import { useState, useEffect, useRef, useCallback } from "react";
import { useWebSocket } from "@/lib/api";
import type { WebSocketStatus } from "@/lib/api";

// ─── Types ───────────────────────────────────────────────────────────────────

export interface ResearchLogProps {
  /** Workbench key like "tool::ItemName" */
  itemKey: string;
  /** Whether to connect to the WebSocket */
  isActive: boolean;
  /** Callback when research finishes */
  onComplete?: () => void;
}

interface LogFrame {
  type: "log" | "done" | "error";
  lines?: string;
  message?: string;
}

// ─── Status Indicator ────────────────────────────────────────────────────────

const STATUS_CONFIG: Record<
  WebSocketStatus,
  { label: string; dotClass: string }
> = {
  connecting: {
    label: "CONNECTING...",
    dotClass: "bg-accent-amber animate-pulse",
  },
  open: {
    label: "LIVE",
    dotClass: "bg-accent-green",
  },
  closed: {
    label: "DISCONNECTED",
    dotClass: "border border-outline bg-transparent",
  },
  error: {
    label: "ERROR",
    dotClass: "bg-red",
  },
};

function ConnectionStatus({ status }: { status: WebSocketStatus }) {
  const config = STATUS_CONFIG[status];
  return (
    <div className="flex items-center gap-2 text-[9px] font-mono uppercase tracking-wider">
      <span className={`h-2 w-2 ${config.dotClass}`} />
      <span
        className={
          status === "open"
            ? "text-accent-green"
            : status === "error"
              ? "text-red"
              : "text-text-secondary"
        }
      >
        {config.label}
      </span>
    </div>
  );
}

// ─── Inner component (always calls hook) ─────────────────────────────────────

function ResearchLogInner({
  itemKey,
  onComplete,
}: {
  itemKey: string;
  onComplete?: () => void;
}) {
  const [lines, setLines] = useState<string[]>([]);
  const [isDone, setIsDone] = useState(false);
  const containerRef = useRef<HTMLDivElement>(null);
  const onCompleteRef = useRef(onComplete);
  onCompleteRef.current = onComplete;

  const handleMessage = useCallback((data: unknown) => {
    const frame = data as LogFrame;

    if (frame.type === "log" || frame.type === "done") {
      if (frame.lines) {
        const newLines = frame.lines.split("\n").filter(Boolean);
        setLines((prev) => {
          const updated = [...prev, ...newLines];
          return updated.length > 500 ? updated.slice(-500) : updated;
        });
      }
    }

    if (frame.type === "done") {
      setIsDone(true);
      onCompleteRef.current?.();
    }

    if (frame.type === "error") {
      const errorMsg = frame.message ?? "Unknown error";
      setLines((prev) => [...prev, `[ERROR] ${errorMsg}`]);
    }
  }, []);

  const wsPath = `/ws/research/${encodeURIComponent(itemKey)}`;

  const { status } = useWebSocket({
    path: wsPath,
    reconnect: !isDone,
    maxRetries: 3,
    onMessage: handleMessage,
  });

  // Auto-scroll on new lines
  useEffect(() => {
    const el = containerRef.current;
    if (el) {
      el.scrollTop = el.scrollHeight;
    }
  }, [lines]);

  // Reset state when itemKey changes
  useEffect(() => {
    setLines([]);
    setIsDone(false);
  }, [itemKey]);

  return (
    <div className="flex flex-col gap-2">
      {/* Header bar */}
      <div className="flex items-center justify-between px-1">
        <span className="text-[9px] font-mono text-accent-cyan/60 uppercase tracking-widest">
          RESEARCH_LOG
        </span>
        <ConnectionStatus status={isDone ? "closed" : status} />
      </div>

      {/* Terminal display */}
      <div
        ref={containerRef}
        className="bg-bg-base border border-accent-cyan/20 p-4 max-h-64 overflow-y-auto font-mono text-[11px] text-accent-cyan/80 leading-relaxed"
      >
        {lines.length === 0 && !isDone && (
          <span className="text-text-secondary/50 italic">
            &gt; Awaiting signal...
          </span>
        )}
        {lines.map((line, i) => (
          <div key={i} className="whitespace-pre-wrap">
            <span className="text-accent-cyan/40 mr-2">&gt;</span>
            {line}
          </div>
        ))}
        {isDone && (
          <div className="mt-3 pt-2 border-t border-accent-cyan/10 text-accent-green font-bold">
            <span className="mr-2">&gt;</span>
            RESEARCH COMPLETE
          </div>
        )}
      </div>
    </div>
  );
}

// ─── Public Component (conditional render gates the hook) ────────────────────

/**
 * ResearchLog — Terminal-style WebSocket log display for research activity.
 * Connects to /ws/research/{key}, accumulates log lines, auto-scrolls.
 * Only mounts the WebSocket connection when isActive is true.
 */
export function ResearchLog({ itemKey, isActive, onComplete }: ResearchLogProps) {
  if (!isActive) return null;
  return <ResearchLogInner itemKey={itemKey} onComplete={onComplete} />;
}

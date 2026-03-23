"use client";

import { useState, useCallback } from "react";
import { mutate as swrMutate } from "swr";
import { Badge } from "@/components/ui/badge";
import { GlowButton } from "@/components/ui/glow-button";
import { apiMutate } from "@/lib/api";
import { useMethods } from "./hooks";
import { FeedSkeleton } from "./Skeleton";
import type { MethodItem } from "./types";

function MethodCard({ item, index }: { item: MethodItem; index: number }) {
  const [expanded, setExpanded] = useState(false);
  const [wbStatus, setWbStatus] = useState<"idle" | "sending" | "sent">("idle");
  const [dismissing, setDismissing] = useState(false);

  const handleDismiss = useCallback(async (e: React.MouseEvent) => {
    e.stopPropagation();
    if (dismissing) return;
    setDismissing(true);
    try {
      await apiMutate(`/status/method::${item.name}`, { body: { status: "dismissed" } });
      await swrMutate("/methods");
    } catch (err) {
      console.error("Dismiss failed:", err);
      setDismissing(false);
    }
  }, [item.name, dismissing]);

  const handleWorkbench = useCallback(async () => {
    if (wbStatus !== "idle") return;
    setWbStatus("sending");
    try {
      await apiMutate("/workbench", {
        body: {
          item: {
            source_type: "method",
            name: item.name,
            category: item.category,
            status: item.status,
            source: item.source,
            notes: item.notes,
            tags: item.tags?.join(", ") ?? "",
          },
        },
      });
      await swrMutate("/workbench");
      setWbStatus("sent");
      setTimeout(() => setWbStatus("idle"), 2000);
    } catch (err) {
      console.error("Workbench send failed:", err);
      setWbStatus("idle");
    }
  }, [item, wbStatus]);

  return (
    <div
      className={`bg-bg-surface p-5 border-l-4 border-purple group transition-all duration-150 cursor-pointer ${
        expanded ? "ring-1 ring-purple/30" : "hover:bg-surface-high/50"
      }`}
      onClick={() => setExpanded((prev) => !prev)}
    >
      <div className="flex justify-between items-start mb-2">
        <div className="flex items-center gap-3">
          <span className="font-mono text-[10px] text-accent-cyan/50">
            [{String(index + 1).padStart(2, "0")}]
          </span>
          <h3 className="font-mono font-bold text-white group-hover:text-accent-cyan transition-colors">
            {item.name}
          </h3>
        </div>
        <Badge variant="method">METHOD</Badge>
      </div>

      {item.category && (
        <span className="text-[9px] font-headline text-outline border border-outline-variant px-1.5 py-0.5 mr-2">
          {item.category.toUpperCase()}
        </span>
      )}

      {item.source && (
        <span className="text-[9px] font-mono text-accent-cyan/60 ml-1">
          via {item.source}
        </span>
      )}

      {item.tags && item.tags.length > 0 && (
        <div className="flex flex-wrap gap-1.5 mt-3">
          {item.tags.map((tag) => (
            <span
              key={tag}
              className="text-[9px] font-mono border border-purple/40 text-purple px-2 py-0.5"
            >
              {tag.toUpperCase()}
            </span>
          ))}
        </div>
      )}

      {item.notes && (
        <p className="font-mono text-[11px] text-text-secondary mt-3 leading-relaxed">
          {item.notes}
        </p>
      )}

      {/* Expanded content */}
      {expanded && (
        <div className="mt-4 pt-4 border-t border-outline-variant/20 space-y-4" onClick={(e) => e.stopPropagation()}>
          {item.paper_url && (
            <div>
              <p className="text-[10px] font-headline font-bold text-text-secondary uppercase tracking-[0.2em] mb-1">
                Paper URL
              </p>
              <a
                href={item.paper_url}
                target="_blank"
                rel="noopener noreferrer"
                className="font-mono text-[11px] text-accent-cyan hover:underline"
              >
                {item.paper_url}
              </a>
            </div>
          )}

          <div className="flex gap-3">
            <GlowButton
              variant="secondary"
              className="flex-1 py-2 text-[10px]"
              onClick={handleWorkbench}
              disabled={wbStatus !== "idle"}
            >
              {wbStatus === "sent" ? "SENT TO WORKBENCH" : wbStatus === "sending" ? "SENDING..." : "SEND TO WORKBENCH"}
            </GlowButton>
            <GlowButton
              variant="secondary"
              className="py-2 text-[10px] px-4"
              onClick={handleDismiss}
              disabled={dismissing}
            >
              {dismissing ? "..." : "DISMISS"}
            </GlowButton>
          </div>
        </div>
      )}
    </div>
  );
}

/**
 * AISignalTab — Methods/techniques intelligence feed with expandable cards and workbench integration.
 */
export function AISignalTab() {
  const { data, isLoading } = useMethods();

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between border-b border-outline-variant/30 pb-2">
        <h2 className="font-headline font-bold text-lg tracking-widest text-cyan-fixed uppercase">
          AI Signal
        </h2>
        <span className="font-mono text-[10px] text-outline">
          {data ? `${data.length} METHODS` : "LOADING..."}
        </span>
      </div>

      <p className="font-mono text-[10px] text-text-secondary">
        METHODS &amp; TECHNIQUES FROM JOURNALCLUB REPORTS
      </p>

      {isLoading || !data ? (
        <FeedSkeleton count={5} />
      ) : (
        <div className="grid grid-cols-1 gap-4 md:grid-cols-2 max-h-[700px] overflow-y-auto pr-2">
          {data.map((item, i) => (
            <MethodCard key={i} item={item} index={i} />
          ))}
          {data.length === 0 && (
            <p className="font-mono text-sm text-text-secondary col-span-2">
              No methods tracked
            </p>
          )}
        </div>
      )}
    </div>
  );
}

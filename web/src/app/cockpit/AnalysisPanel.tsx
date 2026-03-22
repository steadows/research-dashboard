"use client";

import { useState, useCallback } from "react";
import { cn } from "@/lib/utils";
import { apiMutate } from "@/lib/api";
import type { AnalysisResult } from "./types";

interface AnalysisPanelProps {
  projectName: string | null;
}

type AnalysisMode = "quick" | "deep";

/**
 * AnalysisPanel — Analyze (Haiku) + Go Deep (Sonnet) buttons with streaming result display.
 * Matches cockpit.html action buttons and context sources panel.
 */
export function AnalysisPanel({ projectName }: AnalysisPanelProps) {
  const [result, setResult] = useState<AnalysisResult | null>(null);
  const [loading, setLoading] = useState<AnalysisMode | null>(null);
  const [error, setError] = useState<string | null>(null);

  const runAnalysis = useCallback(
    async (mode: AnalysisMode) => {
      if (!projectName || loading) return;

      setLoading(mode);
      setError(null);
      setResult(null);

      try {
        const endpoint =
          mode === "quick" ? "/analyze" : "/analyze/deep";
        const data = await apiMutate<AnalysisResult>(endpoint, {
          body: { project: projectName },
        });
        setResult(data);
      } catch (err) {
        setError(
          err instanceof Error ? err.message : "Analysis failed"
        );
      } finally {
        setLoading(null);
      }
    },
    [projectName, loading]
  );

  return (
    <div className="space-y-4">
      {/* Action buttons */}
      <div className="flex gap-3">
        <button
          onClick={() => runAnalysis("quick")}
          disabled={!projectName || loading !== null}
          className={cn(
            "px-6 py-2 font-heading text-xs font-bold uppercase tracking-widest transition-all",
            "border border-accent-cyan text-accent-cyan",
            "hover:bg-accent-cyan/10",
            "disabled:cursor-not-allowed disabled:opacity-40"
          )}
        >
          {loading === "quick" ? "ANALYZING..." : "ANALYZE"}
        </button>
        <button
          onClick={() => runAnalysis("deep")}
          disabled={!projectName || loading !== null}
          className={cn(
            "px-6 py-2 font-heading text-xs font-bold uppercase tracking-widest transition-all",
            "bg-accent-amber text-bg-base",
            "hover:brightness-110",
            "disabled:cursor-not-allowed disabled:opacity-40"
          )}
        >
          {loading === "deep" ? "DEEP SCAN..." : "GO DEEP"}
        </button>
      </div>

      {/* Error */}
      {error && (
        <div className="border border-accent-red/30 bg-accent-red/5 p-4">
          <p className="font-mono text-xs text-accent-red">{error}</p>
        </div>
      )}

      {/* Result */}
      {result && (
        <div className="space-y-3 border border-outline-variant/10 bg-bg-surface p-4">
          {/* Meta */}
          <div className="flex items-center gap-4 border-b border-outline-variant/10 pb-2">
            <span className="font-mono text-[9px] text-outline">
              MODEL: {result.model.toUpperCase()}
            </span>
            <span className="font-mono text-[9px] text-outline">
              TOKENS: {result.tokens_used.toLocaleString()}
            </span>
            {result.cached && (
              <span className="border border-accent-green/30 bg-accent-green/10 px-1.5 py-0.5 font-mono text-[9px] text-accent-green">
                CACHED
              </span>
            )}
          </div>

          {/* Analysis text */}
          <div className="max-h-80 overflow-y-auto">
            <p className="whitespace-pre-wrap font-sans text-sm leading-relaxed text-text-secondary">
              {result.analysis}
            </p>
          </div>
        </div>
      )}

      {/* Placeholder when no analysis run */}
      {!result && !error && !loading && (
        <div className="border border-outline-variant/10 bg-bg-surface/50 p-6 text-center">
          <p className="font-mono text-[10px] uppercase text-outline/40">
            {projectName
              ? "Run analysis to generate insights"
              : "Select a project first"}
          </p>
        </div>
      )}
    </div>
  );
}

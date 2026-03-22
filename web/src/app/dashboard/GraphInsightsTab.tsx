"use client";

import { DataReadout } from "@/components/ui/data-readout";
import { useGraphHealth } from "./hooks";
import { Skeleton } from "./Skeleton";

/**
 * GraphInsightsTab — Graph health metrics and network overview.
 * Displays key-value metrics from the /api/graph/health endpoint.
 */
export function GraphInsightsTab() {
  const { data, isLoading } = useGraphHealth();

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between border-b border-outline-variant/30 pb-2">
        <h2 className="font-headline font-bold text-lg tracking-widest text-cyan-fixed uppercase">
          Graph Insights
        </h2>
        <span className="font-mono text-[10px] text-outline">
          KNOWLEDGE GRAPH HEALTH
        </span>
      </div>

      {isLoading || !data ? (
        <div className="grid grid-cols-2 gap-6 md:grid-cols-3">
          {Array.from({ length: 6 }, (_, i) => (
            <div key={i} className="bg-bg-surface border border-outline-variant/20 p-4">
              <Skeleton className="h-3 w-20 mb-2" />
              <Skeleton className="h-7 w-16" />
            </div>
          ))}
        </div>
      ) : (
        <>
          <div className="grid grid-cols-2 gap-6 md:grid-cols-3">
            <div className="bg-bg-surface border border-outline-variant/20 p-4">
              <DataReadout label="TOTAL NODES" value={data.total_nodes} color="cyan" />
            </div>
            <div className="bg-bg-surface border border-outline-variant/20 p-4">
              <DataReadout label="TOTAL EDGES" value={data.total_edges} color="cyan" />
            </div>
            <div className="bg-bg-surface border border-outline-variant/20 p-4">
              <DataReadout label="COMPONENTS" value={data.connected_components} color="green" />
            </div>
            <div className="bg-bg-surface border border-outline-variant/20 p-4">
              <DataReadout label="ORPHAN NODES" value={data.orphan_nodes} color={data.orphan_nodes > 5 ? "amber" : "green"} />
            </div>
            <div className="bg-bg-surface border border-outline-variant/20 p-4">
              <DataReadout label="AVG DEGREE" value={(data.avg_degree ?? 0).toFixed(2)} color="cyan" />
            </div>
            <div className="bg-bg-surface border border-outline-variant/20 p-4">
              <DataReadout label="DENSITY" value={(data.density ?? 0).toFixed(4)} color="cyan" />
            </div>
          </div>

          {/* Graph visualization placeholder */}
          <div className="border border-outline-variant/20 bg-bg-surface p-6 mt-4">
            <div className="flex items-center justify-center h-64">
              <div className="text-center space-y-2">
                <div className="flex items-center justify-center">
                  <svg className="h-10 w-10 text-accent-cyan/30" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1}>
                    <path strokeLinecap="round" strokeLinejoin="round" d="M7.5 14.25v2.25m3-4.5v4.5m3-6.75v6.75m3-9v9M3 20.25h18M3.75 3v16.5h16.5" />
                  </svg>
                </div>
                <p className="font-mono text-[10px] text-accent-cyan/40 uppercase tracking-widest">
                  D3 Graph Visualization — Session 22
                </p>
              </div>
            </div>
          </div>
        </>
      )}
    </div>
  );
}

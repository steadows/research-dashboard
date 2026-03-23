"use client";

import { useState } from "react";
import { DataReadout } from "@/components/ui/data-readout";
import { useGraphHealth, useGraphCommunities, useHubNotes } from "./hooks";
import { Skeleton } from "./Skeleton";

/**
 * GraphInsightsTab — Graph health metrics and network overview.
 * Displays key-value metrics from the /api/graph/health endpoint.
 */
export function GraphInsightsTab() {
  const { data, isLoading } = useGraphHealth();
  const { data: communities } = useGraphCommunities();
  const { data: hubNotes } = useHubNotes();
  const [expandedCommunity, setExpandedCommunity] = useState<number | null>(null);

  const filteredCommunities = communities?.filter((c) => c.length >= 3) ?? [];

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

          {/* Hub notes table */}
          {hubNotes && hubNotes.length > 0 && (
            <div className="mt-4 space-y-2">
              <p className="font-mono text-[10px] text-outline uppercase tracking-widest mb-3">
                HUB NOTES — TOP {hubNotes.length} BY PAGERANK
              </p>
              <div className="bg-bg-surface border border-outline-variant/20 overflow-hidden">
                <table className="w-full">
                  <thead>
                    <tr className="border-b border-outline-variant/20 text-[9px] font-mono uppercase tracking-widest text-outline">
                      <th className="text-left px-4 py-2">#</th>
                      <th className="text-left px-4 py-2">Note</th>
                      <th className="text-right px-4 py-2">PageRank</th>
                      <th className="text-right px-4 py-2">In-Degree</th>
                      <th className="text-right px-4 py-2">Betweenness</th>
                    </tr>
                  </thead>
                  <tbody>
                    {hubNotes.map((node, i) => (
                      <tr
                        key={node.name}
                        className="border-b border-outline-variant/10 hover:bg-surface-high/30 transition-colors"
                      >
                        <td className="px-4 py-2 font-mono text-[10px] text-accent-cyan">
                          {String(i + 1).padStart(2, "0")}
                        </td>
                        <td className="px-4 py-2 font-mono text-xs text-text-primary">
                          {node.name}
                        </td>
                        <td className="px-4 py-2 font-mono text-[10px] text-accent-cyan text-right">
                          {node.pagerank.toFixed(4)}
                        </td>
                        <td className="px-4 py-2 font-mono text-[10px] text-text-secondary text-right">
                          {node.in_degree}
                        </td>
                        <td className="px-4 py-2 font-mono text-[10px] text-text-secondary text-right">
                          {node.betweenness.toFixed(4)}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}

          {/* Communities section */}
          {filteredCommunities.length > 0 && (
            <div className="mt-4 space-y-2">
              <p className="font-mono text-[10px] text-outline uppercase tracking-widest mb-3">
                COMMUNITIES ({filteredCommunities.length})
              </p>
              {filteredCommunities.map((members, idx) => {
                const isOpen = expandedCommunity === idx;
                return (
                  <div
                    key={idx}
                    className="bg-bg-surface border border-outline-variant/20"
                  >
                    <button
                      className="w-full flex items-center justify-between px-4 py-3 text-left"
                      onClick={() => setExpandedCommunity(isOpen ? null : idx)}
                    >
                      <span className="font-mono text-xs text-purple-400 font-bold">
                        Community {idx + 1}
                      </span>
                      <span className="font-mono text-[10px] text-outline">
                        {members.length} members {isOpen ? "▲" : "▼"}
                      </span>
                    </button>
                    {isOpen && (
                      <div className="px-4 pb-3 flex flex-wrap gap-2">
                        {members.map((member, mi) => (
                          <span
                            key={mi}
                            className="font-mono text-[10px] bg-purple-400/10 text-purple-300 border border-purple-400/20 px-2 py-0.5"
                          >
                            {member}
                          </span>
                        ))}
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
          )}
        </>
      )}
    </div>
  );
}

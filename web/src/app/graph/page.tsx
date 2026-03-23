"use client";

import { GraphInsightsTab } from "../dashboard/GraphInsightsTab";

/**
 * Graph page — standalone route for knowledge graph health, hub notes,
 * and community detection. Accessible via sidebar graph button.
 */
export default function GraphPage() {
  return (
    <div className="pb-8">
      <div className="mb-10">
        <h1 className="flex items-baseline gap-3 font-heading text-4xl font-black uppercase tracking-tighter text-accent-cyan">
          Graph
          <span className="text-sm font-mono font-normal text-text-muted">
            /Knowledge_Network
          </span>
        </h1>
        <p className="mt-1 font-mono text-xs uppercase text-text-muted">
          Vault Graph Health &amp; Community Intelligence
        </p>
      </div>

      <GraphInsightsTab />
    </div>
  );
}

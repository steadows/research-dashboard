"use client";

import { useState, useCallback } from "react";
import useSWR from "swr";
import { defaultSWRConfig } from "@/lib/api";
import { ProjectSidebar } from "./ProjectSidebar";
import { ProjectHeader } from "./ProjectHeader";
import { GraphVisualization } from "./GraphVisualization";
import { ItemsFeed } from "./ItemsFeed";
import type { Project, ProjectItem, GraphData } from "./types";

/**
 * Cockpit page — Project-scoped workspace with D3 graph, items feed, and analysis.
 *
 * Layout: sidebar (project list) | main area (header, graph, feeds, analysis)
 * Data fetching: SWR hooks keyed on selected project name.
 */
export default function CockpitPage() {
  const [selectedProject, setSelectedProject] = useState<string | null>(null);

  // Fetch project details when selected
  const { data: projects } = useSWR<Project[]>(
    "/projects",
    defaultSWRConfig
  );

  const activeProject = projects?.find((p) => p.name === selectedProject) ?? null;

  // Fetch project items
  const { data: items, isLoading: itemsLoading } = useSWR<ProjectItem[]>(
    selectedProject ? `/project-index/${encodeURIComponent(selectedProject)}` : null,
    defaultSWRConfig
  );

  // Fetch graph visualization data
  const { data: graphData } = useSWR<GraphData>(
    selectedProject ? `/graph/${encodeURIComponent(selectedProject)}/viz` : null,
    defaultSWRConfig
  );

  const handleSelectProject = useCallback((name: string) => {
    setSelectedProject(name);
  }, []);

  const handleNodeClick = useCallback((_nodeId: string) => {
    // Future: scroll to item in feed or highlight it
  }, []);

  const emptyGraph: GraphData = { nodes: [], edges: [] };

  return (
    <div className="-m-6 flex h-[calc(100vh-64px)]">
      {/* Project sidebar */}
      <ProjectSidebar
        selectedProject={selectedProject}
        onSelectProject={handleSelectProject}
      />

      {/* Main content area */}
      <div className="flex-1 overflow-y-auto p-8">
        {!activeProject ? (
          /* Empty state */
          <div className="flex h-full flex-col items-center justify-center gap-4">
            <svg
              className="h-16 w-16 text-outline/20"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
              strokeWidth={0.5}
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                d="M3.75 9.776c.112-.017.227-.026.344-.026h15.812c.117 0 .232.009.344.026m-16.5 0a2.25 2.25 0 00-1.883 2.542l.857 6a2.25 2.25 0 002.227 1.932H19.05a2.25 2.25 0 002.227-1.932l.857-6a2.25 2.25 0 00-1.883-2.542m-16.5 0V6A2.25 2.25 0 016 3.75h3.879a1.5 1.5 0 011.06.44l2.122 2.12a1.5 1.5 0 001.06.44H18A2.25 2.25 0 0120.25 9v.776"
              />
            </svg>
            <p className="font-heading text-sm uppercase tracking-widest text-outline/50">
              Select a project to begin
            </p>
            <p className="font-mono text-[10px] text-outline/30">
              COCKPIT_STANDBY // AWAITING_TARGET
            </p>
          </div>
        ) : (
          <div className="space-y-6">
            {/* Project header */}
            <ProjectHeader project={activeProject} />

            {/* Items feed — primary content, above the fold */}
            <ItemsFeed items={items ?? []} isLoading={itemsLoading} project={activeProject} />

            {/* Graph + compact stats row */}
            <div className="grid grid-cols-12 gap-4">
              {/* Graph visualization — compact */}
              <div className="col-span-12 border border-outline-variant/10 bg-bg-surface/50 p-4 lg:col-span-8">
                <GraphVisualization
                  data={graphData ?? emptyGraph}
                  onNodeClick={handleNodeClick}
                />
              </div>

              {/* Compact stats */}
              <div className="col-span-12 flex flex-col gap-4 lg:col-span-4">
                <div className="border border-outline-variant/10 bg-bg-surface/50 p-4">
                  <div className="font-mono text-[10px] uppercase tracking-widest text-outline">
                    LINKED_ITEMS
                  </div>
                  <div className="mt-1 font-mono text-2xl font-black text-accent-cyan">
                    {items?.length ?? "--"}
                  </div>
                  <div className="mt-3 h-1 w-full bg-outline-variant/20">
                    <div
                      className="h-full bg-accent-cyan transition-all"
                      style={{
                        width: items
                          ? `${Math.min((items.length / 20) * 100, 100)}%`
                          : "0%",
                      }}
                    />
                  </div>
                </div>

                <div className="border border-outline-variant/10 bg-bg-surface/50 p-4">
                  <div className="font-mono text-[10px] uppercase tracking-widest text-outline">
                    GRAPH_NODES
                  </div>
                  <div className="mt-1 font-mono text-2xl font-black text-accent-green">
                    {graphData?.nodes.length ?? "--"}
                  </div>
                  <div className="mt-3 flex gap-1">
                    {[1, 2, 3, 4].map((i) => (
                      <div
                        key={i}
                        className={`h-1 w-2 ${
                          graphData && i <= Math.ceil(graphData.nodes.length / 5)
                            ? "bg-accent-green"
                            : "bg-accent-green/30"
                        }`}
                      />
                    ))}
                  </div>
                </div>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

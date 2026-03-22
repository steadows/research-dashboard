"use client";

import { useRef, useEffect, useCallback, useState } from "react";
import * as d3 from "d3";
import type { GraphData, SimNode, SimEdge } from "./types";
import { NODE_COLORS, EDGE_STYLES, NODE_RADIUS } from "./types";

interface GraphVisualizationProps {
  data: GraphData;
  className?: string;
  onNodeClick?: (nodeId: string) => void;
}

/**
 * D3 force-directed graph rendered into a React-managed SVG container.
 *
 * Integration pattern:
 * - React owns the <svg> element via useRef
 * - D3 owns all DOM inside the SVG via useEffect
 * - D3 simulation cleaned up on unmount or data change
 * - Zoom/pan via d3-zoom on the SVG
 * - Tooltip positioned via pointer events (React state)
 */
export function GraphVisualization({
  data,
  className,
  onNodeClick,
}: GraphVisualizationProps) {
  const svgRef = useRef<SVGSVGElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);
  const [tooltip, setTooltip] = useState<{
    x: number;
    y: number;
    label: string;
    type: string;
  } | null>(null);

  const renderGraph = useCallback(() => {
    const svg = svgRef.current;
    const container = containerRef.current;
    if (!svg || !container) return;

    const width = container.clientWidth;
    const height = container.clientHeight;

    // Clear previous render
    d3.select(svg).selectAll("*").remove();

    // Empty state
    if (data.nodes.length === 0) return;

    // Build simulation data (immutable copy)
    const simNodes: SimNode[] = data.nodes.map((n) => ({
      ...n,
      x: width / 2 + (Math.random() - 0.5) * 100,
      y: height / 2 + (Math.random() - 0.5) * 100,
    }));

    const nodeMap = new Map(simNodes.map((n) => [n.id, n]));

    const simEdges: SimEdge[] = data.edges
      .filter((e) => nodeMap.has(e.source) && nodeMap.has(e.target))
      .map((e) => ({
        source: e.source,
        target: e.target,
        relation: e.relation,
      }));

    // SVG setup
    const svgSelection = d3
      .select(svg)
      .attr("width", width)
      .attr("height", height)
      .attr("viewBox", `0 0 ${width} ${height}`);

    // Zoom container
    const g = svgSelection.append("g");

    const zoom = d3
      .zoom<SVGSVGElement, unknown>()
      .scaleExtent([0.3, 3])
      .on("zoom", (event) => {
        g.attr("transform", event.transform);
      });

    svgSelection.call(zoom);

    // Edge glow filter
    const defs = svgSelection.append("defs");
    const glowFilter = defs.append("filter").attr("id", "edge-glow");
    glowFilter
      .append("feGaussianBlur")
      .attr("stdDeviation", "2")
      .attr("result", "coloredBlur");
    const feMerge = glowFilter.append("feMerge");
    feMerge.append("feMergeNode").attr("in", "coloredBlur");
    feMerge.append("feMergeNode").attr("in", "SourceGraphic");

    // Draw edges
    const edgeGroup = g
      .append("g")
      .attr("class", "edges")
      .selectAll("line")
      .data(simEdges)
      .join("line")
      .attr("stroke", (d) => EDGE_STYLES[d.relation].color)
      .attr("stroke-width", 1)
      .attr("stroke-opacity", 0.5)
      .attr("stroke-dasharray", (d) => EDGE_STYLES[d.relation].dasharray)
      .attr("filter", "url(#edge-glow)");

    // Draw nodes
    const nodeGroup = g
      .append("g")
      .attr("class", "nodes")
      .selectAll("circle")
      .data(simNodes)
      .join("circle")
      .attr("r", (d) => NODE_RADIUS[d.type])
      .attr("fill", (d) => NODE_COLORS[d.type])
      .attr("fill-opacity", 0.8)
      .attr("stroke", (d) => NODE_COLORS[d.type])
      .attr("stroke-width", 1.5)
      .attr("stroke-opacity", 0.4)
      .attr("cursor", "pointer")
      .on("mouseenter", (_event, d) => {
        const svgRect = svg.getBoundingClientRect();
        setTooltip({
          x: (d.x ?? 0) + svgRect.left,
          y: (d.y ?? 0) + svgRect.top - 20,
          label: d.label,
          type: d.type,
        });
        d3.select(_event.currentTarget)
          .transition()
          .duration(100)
          .attr("r", NODE_RADIUS[d.type] * 1.6)
          .attr("fill-opacity", 1);
      })
      .on("mouseleave", (_event, d) => {
        setTooltip(null);
        d3.select(_event.currentTarget)
          .transition()
          .duration(100)
          .attr("r", NODE_RADIUS[d.type])
          .attr("fill-opacity", 0.8);
      })
      .on("click", (_event, d) => {
        onNodeClick?.(d.id);
      });

    // Drag behavior
    const drag = d3
      .drag<SVGCircleElement, SimNode>()
      .on("start", (event, d) => {
        if (!event.active) simulation.alphaTarget(0.3).restart();
        d.fx = d.x;
        d.fy = d.y;
      })
      .on("drag", (event, d) => {
        d.fx = event.x;
        d.fy = event.y;
      })
      .on("end", (event, d) => {
        if (!event.active) simulation.alphaTarget(0);
        d.fx = null;
        d.fy = null;
      });

    (nodeGroup as d3.Selection<SVGCircleElement, SimNode, SVGGElement, unknown>).call(drag);

    // Force simulation
    const simulation = d3
      .forceSimulation(simNodes)
      .force(
        "link",
        d3
          .forceLink<SimNode, SimEdge>(simEdges)
          .id((d) => d.id)
          .distance(80)
      )
      .force("charge", d3.forceManyBody().strength(-200))
      .force("center", d3.forceCenter(width / 2, height / 2))
      .force("collision", d3.forceCollide().radius((d) => NODE_RADIUS[(d as SimNode).type] + 4))
      .on("tick", () => {
        edgeGroup
          .attr("x1", (d) => (d.source as SimNode).x ?? 0)
          .attr("y1", (d) => (d.source as SimNode).y ?? 0)
          .attr("x2", (d) => (d.target as SimNode).x ?? 0)
          .attr("y2", (d) => (d.target as SimNode).y ?? 0);

        nodeGroup.attr("cx", (d) => d.x ?? 0).attr("cy", (d) => d.y ?? 0);
      });

    // Store simulation ref for cleanup
    return simulation;
  }, [data, onNodeClick]);

  useEffect(() => {
    const simulation = renderGraph();

    const handleResize = () => {
      renderGraph();
    };

    const resizeObserver = new ResizeObserver(handleResize);
    if (containerRef.current) {
      resizeObserver.observe(containerRef.current);
    }

    return () => {
      simulation?.stop();
      resizeObserver.disconnect();
    };
  }, [renderGraph]);

  const isEmpty = data.nodes.length === 0;

  return (
    <div className={className}>
      {/* Header */}
      <div className="mb-4 flex items-start justify-between">
        <div>
          <div className="font-mono text-[10px] uppercase tracking-widest text-accent-cyan">
            NETWORK_TOPOLOGY_01
          </div>
          <h3 className="font-heading text-lg font-bold uppercase tracking-wider text-text-primary">
            Neural Map Viz
          </h3>
        </div>
        {!isEmpty && (
          <div className="text-right">
            <div className="font-mono text-[10px] uppercase tracking-widest text-outline">
              Nodes
            </div>
            <div className="font-mono text-2xl font-black text-text-primary">
              {data.nodes.length}
              <span className="text-sm font-normal text-outline">
                /{data.edges.length}
              </span>
            </div>
          </div>
        )}
      </div>

      {/* Graph container */}
      <div
        ref={containerRef}
        className="relative flex min-h-[300px] items-center justify-center border border-outline-variant/10 bg-black/40"
      >
        {isEmpty ? (
          <div className="flex flex-col items-center gap-3 py-12">
            <svg
              className="h-12 w-12 text-outline/30"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
              strokeWidth={1}
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                d="M7.5 14.25v2.25m3-4.5v4.5m3-6.75v6.75m3-9v9M3 20.25h18M3.75 3v16.5h16.5"
              />
            </svg>
            <p className="font-mono text-xs uppercase tracking-wider text-outline/50">
              No graph data available
            </p>
            <p className="font-mono text-[10px] text-outline/30">
              Select a project with linked items to visualize
            </p>
          </div>
        ) : (
          <svg ref={svgRef} className="h-full w-full" />
        )}

        {/* Render latency decoration */}
        <div className="absolute bottom-2 right-2 font-mono text-[9px] text-outline/30">
          RENDER_MODE: D3_FORCE
        </div>
      </div>

      {/* Tooltip — rendered in React, positioned from D3 hover events */}
      {tooltip && (
        <div
          className="pointer-events-none fixed z-50 border border-accent-cyan/30 bg-bg-surface/95 px-3 py-1.5 font-mono text-xs text-text-primary backdrop-blur-sm box-glow-cyan"
          style={{
            left: tooltip.x,
            top: tooltip.y,
            transform: "translate(-50%, -100%)",
          }}
        >
          <span
            className="mr-2 inline-block h-2 w-2"
            style={{ backgroundColor: NODE_COLORS[tooltip.type as keyof typeof NODE_COLORS] }}
          />
          {tooltip.label}
          <span className="ml-2 text-[9px] uppercase text-outline">
            {tooltip.type}
          </span>
        </div>
      )}

      {/* Legend */}
      <div className="mt-3 flex flex-wrap gap-4">
        {(Object.entries(NODE_COLORS) as [string, string][]).map(
          ([type, color]) => (
            <div key={type} className="flex items-center gap-1.5">
              <span
                className="inline-block h-2 w-2"
                style={{ backgroundColor: color }}
              />
              <span className="font-mono text-[9px] uppercase text-outline">
                {type}
              </span>
            </div>
          )
        )}
      </div>
    </div>
  );
}

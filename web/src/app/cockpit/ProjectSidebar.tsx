"use client";

import { useState, useMemo } from "react";
import useSWR from "swr";
import { cn } from "@/lib/utils";
import { defaultSWRConfig } from "@/lib/api";
import type { Project } from "./types";

interface ProjectSidebarProps {
  selectedProject: string | null;
  onSelectProject: (name: string) => void;
}

/**
 * ProjectSidebar — Scrollable project list with search, active glow, and status badges.
 * Matches cockpit.html sidebar design: cyan glow on active, status/domain badges.
 */
export function ProjectSidebar({
  selectedProject,
  onSelectProject,
}: ProjectSidebarProps) {
  const [search, setSearch] = useState("");

  const { data: projects, isLoading } = useSWR<Project[]>(
    "/projects",
    defaultSWRConfig
  );

  const filtered = useMemo(() => {
    if (!projects) return [];
    if (!search.trim()) return projects;
    const q = search.toLowerCase();
    return projects.filter(
      (p) =>
        p.name.toLowerCase().includes(q) ||
        p.domain.toLowerCase().includes(q) ||
        p.tech.some((t) => t.toLowerCase().includes(q))
    );
  }, [projects, search]);

  return (
    <aside className="flex h-full w-72 flex-col border-r border-outline-variant/15 bg-bg-surface/80">
      {/* Header */}
      <div className="px-4 pb-3 pt-4">
        <div className="mb-1 flex items-center gap-3">
          <div className="h-2 w-2 animate-pulse bg-accent-cyan" />
          <span className="font-heading text-xs font-bold uppercase tracking-widest text-cyan-fixed">
            PROJECTS
          </span>
        </div>
        <div className="font-mono text-[10px] text-outline/60">
          [01] SELECTOR_ACTIVE
        </div>
      </div>

      {/* Search */}
      <div className="px-4 pb-3">
        <div className="flex items-center border border-outline-variant/30 bg-bg-base px-3 py-1.5">
          <svg
            className="mr-2 h-3.5 w-3.5 text-outline"
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
            strokeWidth={1.5}
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              d="M21 21l-5.197-5.197m0 0A7.5 7.5 0 105.196 5.196a7.5 7.5 0 0010.607 10.607z"
            />
          </svg>
          <input
            type="text"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="FILTER..."
            className="w-full border-none bg-transparent p-0 font-mono text-xs text-text-primary placeholder:text-outline/40 focus:outline-none focus:ring-0"
          />
        </div>
      </div>

      {/* Project list */}
      <div className="flex-1 space-y-1 overflow-y-auto">
        {isLoading && (
          <div className="px-4 py-8 text-center">
            <div className="inline-block h-4 w-4 animate-pulse bg-accent-cyan/30" />
            <p className="mt-2 font-mono text-[10px] text-outline/50">
              LOADING_PROJECTS...
            </p>
          </div>
        )}

        {!isLoading && filtered.length === 0 && (
          <div className="px-4 py-8 text-center font-mono text-[10px] text-outline/50">
            NO_RESULTS
          </div>
        )}

        {filtered.map((project) => {
          const isActive = project.name === selectedProject;
          return (
            <button
              key={project.name}
              onClick={() => onSelectProject(project.name)}
              className={cn(
                "mx-2 flex w-[calc(100%-1rem)] cursor-pointer items-center justify-between p-3 text-left transition-all duration-75",
                isActive
                  ? "border border-accent-cyan bg-surface-high text-accent-cyan box-glow-cyan"
                  : "border border-transparent text-text-secondary/70 hover:bg-surface-high hover:text-accent-cyan"
              )}
            >
              <div className="flex items-center gap-3 overflow-hidden">
                <svg
                  className="h-4 w-4 shrink-0"
                  fill="none"
                  viewBox="0 0 24 24"
                  stroke="currentColor"
                  strokeWidth={1.5}
                >
                  {isActive ? (
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      d="M3.75 9.776c.112-.017.227-.026.344-.026h15.812c.117 0 .232.009.344.026m-16.5 0a2.25 2.25 0 00-1.883 2.542l.857 6a2.25 2.25 0 002.227 1.932H19.05a2.25 2.25 0 002.227-1.932l.857-6a2.25 2.25 0 00-1.883-2.542m-16.5 0V6A2.25 2.25 0 016 3.75h3.879a1.5 1.5 0 011.06.44l2.122 2.12a1.5 1.5 0 001.06.44H18A2.25 2.25 0 0120.25 9v.776"
                    />
                  ) : (
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      d="M2.25 12.75V12A2.25 2.25 0 014.5 9.75h15A2.25 2.25 0 0121.75 12v.75m-8.69-6.44l-2.12-2.12a1.5 1.5 0 00-1.061-.44H4.5A2.25 2.25 0 002.25 6v12a2.25 2.25 0 002.25 2.25h15A2.25 2.25 0 0021.75 18V9a2.25 2.25 0 00-2.25-2.25h-5.379a1.5 1.5 0 01-1.06-.44z"
                    />
                  )}
                </svg>
                <span className="truncate font-mono text-xs uppercase">
                  {project.name}
                </span>
              </div>
              {isActive && (
                <span className="shrink-0 border border-accent-cyan/40 bg-accent-cyan/20 px-1 font-mono text-[9px]">
                  ACTIVE
                </span>
              )}
            </button>
          );
        })}
      </div>

      {/* Footer */}
      <div className="border-t border-outline-variant/10 px-4 py-3">
        <div className="font-mono text-[9px] text-outline/40">
          {projects ? `${projects.length} PROJECTS` : "---"} // SESSION_22
        </div>
      </div>
    </aside>
  );
}

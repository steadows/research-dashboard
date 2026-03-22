"use client";

import { GlitchText } from "@/components/effects/GlitchText";
import { Badge } from "@/components/ui/badge";
import type { Project } from "./types";

interface ProjectHeaderProps {
  project: Project;
}

/**
 * ProjectHeader — Project name (GlitchText), status/domain badges, tech tags.
 * Matches cockpit.html header: large glitch title, status badges, tech pills.
 */
export function ProjectHeader({ project }: ProjectHeaderProps) {
  return (
    <div className="flex flex-col gap-6 md:flex-row md:items-end md:justify-between">
      <div className="space-y-2">
        {/* Ref line */}
        <div className="flex items-center gap-2 font-mono text-[10px] text-outline">
          <span>PRJ_REF: {project.name.slice(0, 3).toUpperCase()}-{Math.abs(hashCode(project.name)) % 1000}</span>
          <span className="h-1 w-1 rounded-full bg-outline/40" />
          <span>DOMAIN: {project.domain.toUpperCase()}</span>
        </div>

        {/* Title */}
        <GlitchText
          as="h1"
          glowColor="cyan"
          className="font-heading text-4xl font-black uppercase tracking-tighter text-text-primary lg:text-5xl"
        >
          {project.name}
        </GlitchText>

        {/* Badges */}
        <div className="flex flex-wrap items-center gap-3 pt-1">
          <Badge
            variant={project.status === "active" ? "journalclub" : "default"}
            className="tracking-widest"
          >
            STATUS: {project.status.toUpperCase()}
          </Badge>
          <Badge variant="default" className="border-accent-cyan text-accent-cyan bg-accent-cyan/10 tracking-widest">
            DOMAIN: {project.domain.toUpperCase()}
          </Badge>
          <div className="flex gap-2">
            {project.tech.map((t) => (
              <span
                key={t}
                className="border border-outline-variant px-2 py-0.5 font-mono text-[10px] text-outline"
              >
                {t}
              </span>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}

/** Simple string hash for generating pseudo-random ref numbers */
function hashCode(s: string): number {
  let hash = 0;
  for (let i = 0; i < s.length; i++) {
    const char = s.charCodeAt(i);
    hash = ((hash << 5) - hash) + char;
    hash |= 0;
  }
  return hash;
}

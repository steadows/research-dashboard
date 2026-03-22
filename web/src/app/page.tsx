"use client";

import { MetricCard } from "@/components/ui/metric-card";
import { ContentPanel } from "@/components/layout/ContentPanel";
import { GlowButton } from "@/components/ui/glow-button";
import { StatusBadge } from "@/components/ui/status-badge";

export default function DashboardPage() {
  return (
    <div className="space-y-8">
      {/* HUD Metric Cards */}
      <section className="grid grid-cols-1 gap-6 sm:grid-cols-2 lg:grid-cols-4">
        <MetricCard
          index="[01]"
          title="Papers"
          value="--"
          delta="LOADING"
          deltaColor="cyan"
          meta="40.7128° N"
        />
        <MetricCard
          index="[02]"
          title="Tools"
          value="--"
          delta="SYNCED"
          deltaColor="amber"
          meta="74.0060° W"
        />
        <MetricCard
          index="[03]"
          title="Blog Queue"
          value="--"
          delta=""
          meta="EST. 14:00"
        />
        <MetricCard
          index="[04]"
          title="Active Projects"
          value="--"
          delta=""
          deltaColor="green"
          meta="AUTH: LVL 5"
        />
      </section>

      {/* Main Layout Grid */}
      <div className="grid grid-cols-1 gap-8 lg:grid-cols-3">
        {/* Research Feed (2/3) */}
        <ContentPanel label="RESEARCH FEED" status="LIVE" className="lg:col-span-2">
          <div className="flex items-center justify-between border-b border-outline-variant/30 pb-2">
            <h2 className="font-headline text-lg font-bold uppercase tracking-widest text-cyan-fixed">
              Research Feed
            </h2>
            <span className="font-mono text-[10px] text-outline">
              LATEST UPDATES // PAGE 01
            </span>
          </div>
          <div className="mt-4 space-y-4">
            <p className="font-mono text-sm text-text-secondary">
              Feed data will be loaded from /api/status/reports
            </p>
            <StatusBadge status="online" label="API CONNECTED" />
          </div>
        </ContentPanel>

        {/* Tools Radar (1/3) */}
        <ContentPanel label="TOOLS RADAR">
          <div className="flex items-center justify-between border-b border-outline-variant/30 pb-2">
            <h2 className="font-headline text-lg font-bold uppercase tracking-widest text-cyan-fixed">
              Tools Radar
            </h2>
          </div>
          <div className="mt-4 space-y-4">
            <p className="font-mono text-sm text-text-secondary">
              Tools data from /api/status/tools
            </p>
          </div>
        </ContentPanel>
      </div>

      {/* Weekly Signal */}
      <ContentPanel label="WEEKLY SIGNAL">
        <div className="flex items-center justify-between">
          <h2 className="font-headline text-lg font-bold uppercase tracking-widest text-cyan-fixed">
            Weekly Signal
          </h2>
        </div>
        <div className="mt-4 h-48 border border-outline-variant/20 bg-bg-surface p-4">
          <p className="font-mono text-sm text-text-secondary">
            D3.js chart — Session 21
          </p>
        </div>
      </ContentPanel>

      {/* Action buttons */}
      <div className="flex gap-4">
        <GlowButton variant="primary">SCAN INTEL</GlowButton>
        <GlowButton variant="secondary">VIEW ARCHIVE</GlowButton>
      </div>
    </div>
  );
}

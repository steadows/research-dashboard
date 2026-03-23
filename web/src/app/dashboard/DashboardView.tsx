"use client";

import { useState, lazy, Suspense } from "react";
import { TabBar } from "./TabBar";
import { HomeTab } from "./HomeTab";
import { FeedSkeleton } from "./Skeleton";
import type { DashboardTab } from "./types";

// Lazy-load non-default tabs for code splitting
const BlogQueueTab = lazy(() =>
  import("./BlogQueueTab").then((m) => ({ default: m.BlogQueueTab }))
);
const ResearchArchiveTab = lazy(() =>
  import("./ResearchArchiveTab").then((m) => ({ default: m.ResearchArchiveTab }))
);
const ToolsRadarTab = lazy(() =>
  import("./ToolsRadarTab").then((m) => ({ default: m.ToolsRadarTab }))
);

function TabFallback() {
  return (
    <div className="pt-6">
      <FeedSkeleton count={3} />
    </div>
  );
}

/**
 * DashboardView — Client-side dashboard shell with tab navigation.
 * Renders the active tab based on state; default is Home.
 */
export function DashboardView() {
  const [activeTab, setActiveTab] = useState<DashboardTab>("home");

  return (
    <div className="space-y-6">
      <TabBar activeTab={activeTab} onTabChange={setActiveTab} />

      <div id={`tabpanel-${activeTab}`} role="tabpanel" aria-labelledby={activeTab}>
        <Suspense fallback={<TabFallback />}>
          {activeTab === "home" && <HomeTab />}
          {activeTab === "blog-queue" && <BlogQueueTab />}
          {activeTab === "research-archive" && <ResearchArchiveTab />}
          {activeTab === "tools-radar" && <ToolsRadarTab />}
        </Suspense>
      </div>
    </div>
  );
}

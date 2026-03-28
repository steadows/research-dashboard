"use client";

import { useState, lazy, Suspense, useEffect } from "react";
import { useSearchParams, useRouter } from "next/navigation";
import { TabBar } from "./TabBar";
import { HomeTab } from "./HomeTab";
import { FeedSkeleton } from "./Skeleton";
import type { DashboardTab } from "./types";
import { DASHBOARD_TABS } from "./types";

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
const AgenticHubTab = lazy(() =>
  import("./AgenticHubTab").then((m) => ({ default: m.AgenticHubTab }))
);

function TabFallback() {
  return (
    <div className="pt-6">
      <FeedSkeleton count={3} />
    </div>
  );
}

const VALID_TABS = new Set(DASHBOARD_TABS.map((t) => t.id));

/**
 * DashboardView — Client-side dashboard shell with tab navigation.
 * Persists active tab in URL query param (?tab=...) so page refresh
 * returns to the same tab.
 */
export function DashboardView() {
  const searchParams = useSearchParams();
  const router = useRouter();

  const tabParam = searchParams.get("tab") as DashboardTab | null;
  const initialTab = tabParam && VALID_TABS.has(tabParam) ? tabParam : "home";
  const [activeTab, setActiveTab] = useState<DashboardTab>(initialTab);

  // Sync URL when tab changes
  useEffect(() => {
    const current = searchParams.get("tab");
    if (current !== activeTab) {
      const params = new URLSearchParams(searchParams.toString());
      if (activeTab === "home") {
        params.delete("tab");
      } else {
        params.set("tab", activeTab);
      }
      const qs = params.toString();
      router.replace(qs ? `?${qs}` : "/", { scroll: false });
    }
  }, [activeTab, searchParams, router]);

  return (
    <div className="space-y-6">
      <TabBar activeTab={activeTab} onTabChange={setActiveTab} />

      <div id={`tabpanel-${activeTab}`} role="tabpanel" aria-labelledby={activeTab}>
        <Suspense fallback={<TabFallback />}>
          {activeTab === "home" && <HomeTab />}
          {activeTab === "blog-queue" && <BlogQueueTab />}
          {activeTab === "research-archive" && <ResearchArchiveTab />}
          {activeTab === "tools-radar" && <ToolsRadarTab />}
          {activeTab === "agentic-hub" && <AgenticHubTab />}
        </Suspense>
      </div>
    </div>
  );
}

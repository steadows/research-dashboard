"use client";

import { useRef, useEffect, useState } from "react";
import { cn } from "@/lib/utils";
import { DASHBOARD_TABS, type DashboardTab } from "./types";

interface TabBarProps {
  activeTab: DashboardTab;
  onTabChange: (tab: DashboardTab) => void;
}

/**
 * TabBar — Horizontal tab navigation for dashboard views.
 * HUD-style design with active glow indicator. Scrollable on mobile.
 */
export function TabBar({ activeTab, onTabChange }: TabBarProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const [indicatorStyle, setIndicatorStyle] = useState({ left: 0, width: 0 });

  useEffect(() => {
    const container = containerRef.current;
    if (!container) return;

    const activeButton = container.querySelector<HTMLButtonElement>(
      `[data-tab="${activeTab}"]`
    );
    if (!activeButton) return;

    setIndicatorStyle({
      left: activeButton.offsetLeft,
      width: activeButton.offsetWidth,
    });
  }, [activeTab]);

  return (
    <div className="relative border-b border-outline-variant/30">
      <div
        ref={containerRef}
        className="flex gap-0 overflow-x-auto scrollbar-hide"
      >
        {DASHBOARD_TABS.map(({ id, label }) => {
          const isActive = activeTab === id;
          return (
            <button
              key={id}
              data-tab={id}
              onClick={() => onTabChange(id)}
              className={cn(
                "shrink-0 px-4 py-3 font-headline text-[11px] uppercase tracking-[0.15em] transition-colors",
                isActive
                  ? "text-accent-cyan"
                  : "text-text-secondary/60 hover:text-accent-cyan/80"
              )}
            >
              {label}
            </button>
          );
        })}
      </div>

      {/* Active indicator line */}
      <div
        className="absolute bottom-0 h-[2px] bg-accent-cyan transition-all duration-200 box-glow-cyan"
        style={{
          left: indicatorStyle.left,
          width: indicatorStyle.width,
        }}
      />
    </div>
  );
}

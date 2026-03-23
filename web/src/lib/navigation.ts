/** Header navigation routes — primary page-level navigation */
export const NAV_ROUTES = [
  { href: "/", label: "DASHBOARD" },
  { href: "/cockpit", label: "COCKPIT" },
  { href: "/workbench", label: "WORKBENCH" },
  { href: "/agentic-hub", label: "AGENTIC HUB" },
] as const;

/** Sidebar utility routes — secondary tools (not page navigation) */
export const SIDEBAR_ROUTES = [
  { href: "/archive", label: "ARCHIVE" },
  { href: "/graph", label: "GRAPH" },
  { href: "/reports", label: "REPORTS" },
] as const;

export type NavRoute = (typeof NAV_ROUTES)[number];
export type SidebarRoute = (typeof SIDEBAR_ROUTES)[number];

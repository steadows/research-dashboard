/** Shared navigation routes — single source of truth for Header + Sidebar */
export const NAV_ROUTES = [
  { href: "/", label: "DASHBOARD", sidebarLabel: "INTEL" },
  { href: "/cockpit", label: "COCKPIT", sidebarLabel: "SENSORS" },
  { href: "/workbench", label: "WORKBENCH", sidebarLabel: "UPLINK" },
  { href: "/agentic-hub", label: "AGENTIC HUB", sidebarLabel: "ARCHIVE" },
] as const;

export type NavRoute = (typeof NAV_ROUTES)[number];

import useSWR from "swr";
import { defaultSWRConfig } from "@/lib/api";
import type {
  DashboardStats,
  BlogItem,
  ToolItem,
  MethodItem,
  ReportItem,
  GraphHealth,
  InstagramPost,
} from "./types";

/** Dashboard stats — metric card counts */
export function useDashboardStats() {
  return useSWR<DashboardStats>("/dashboard/stats", {
    ...defaultSWRConfig,
    refreshInterval: 30_000,
  });
}

/** Blog queue items */
export function useBlogQueue() {
  return useSWR<BlogItem[]>("/blog-queue", defaultSWRConfig);
}

/** Tools radar items */
export function useTools() {
  return useSWR<ToolItem[]>("/tools", defaultSWRConfig);
}

/** Methods items */
export function useMethods() {
  return useSWR<MethodItem[]>("/methods", defaultSWRConfig);
}

/** Reports — JournalClub + TLDR archives */
export function useReports() {
  return useSWR<ReportItem[]>("/reports", defaultSWRConfig);
}

/** Graph health metrics */
export function useGraphHealth() {
  return useSWR<GraphHealth>("/graph/health", defaultSWRConfig);
}

/** Instagram / Agentic Hub feed */
export function useInstagramFeed() {
  return useSWR<InstagramPost[]>("/instagram/feed", defaultSWRConfig);
}

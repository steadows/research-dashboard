import useSWR from "swr";
import { defaultSWRConfig } from "@/lib/api";
import type {
  DashboardStats,
  BlogItem,
  ToolItem,
  MethodItem,
  ReportItem,
  PaperItem,
  GraphHealth,
  InstagramPost,
  HomeSummary,
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

/** Home summary — cross-source intel brief */
export function useHomeSummary() {
  return useSWR<HomeSummary>("/dashboard/home-summary", defaultSWRConfig);
}

/** Papers — individual papers from JournalClub reports */
export function usePapers() {
  return useSWR<PaperItem[]>("/papers", defaultSWRConfig);
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

/** Graph communities */
export function useGraphCommunities() {
  return useSWR<string[][]>("/graph/communities", defaultSWRConfig);
}

/** Hub notes — top PageRank nodes */
export interface HubNote {
  name: string;
  pagerank: number;
  in_degree: number;
  betweenness: number;
}

export function useHubNotes() {
  return useSWR<HubNote[]>("/graph/hub-notes", defaultSWRConfig);
}

import useSWR from "swr";
import { defaultSWRConfig } from "@/lib/api";

export interface ReportMeta {
  slug: string;
  title: string;
  source_type: string;
  researched: string;
  excerpt: string;
  has_html: boolean;
  source_label?: string;
}

/** Fetch the list of all research reports */
export function useReports() {
  return useSWR<ReportMeta[]>("/research/reports", {
    ...defaultSWRConfig,
    revalidateOnFocus: true,
  });
}

/** Fetch the markdown content of a single report */
export function useReportContent(slug: string | null) {
  return useSWR<{ slug: string; content: string }>(
    slug ? `/research/reports/${slug}/content` : null,
    defaultSWRConfig
  );
}

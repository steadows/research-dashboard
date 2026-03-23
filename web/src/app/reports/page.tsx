"use client";

import { useState, useCallback } from "react";
import { AnimatePresence, m, useReducedMotion } from "framer-motion";
import { Badge } from "@/components/ui/badge";
import { GlowButton } from "@/components/ui/glow-button";
import { useReports, useReportContent } from "./hooks";
import type { ReportMeta } from "./hooks";

const SOURCE_BADGE: Record<string, "tool" | "method" | "instagram"> = {
  tool: "tool",
  method: "method",
  instagram: "instagram",
};

const SOURCE_BORDER: Record<string, string> = {
  tool: "border-accent-green",
  method: "border-purple",
  instagram: "border-indigo",
};

function ReportCard({
  report,
  isSelected,
  onSelect,
}: {
  report: ReportMeta;
  isSelected: boolean;
  onSelect: (slug: string) => void;
}) {
  const border = SOURCE_BORDER[report.source_type] ?? "border-outline-variant";
  const badgeVariant = SOURCE_BADGE[report.source_type] ?? "tool";

  return (
    <button
      onClick={() => onSelect(report.slug)}
      className={`w-full text-left border-l-4 ${border} bg-bg-surface p-4 transition-all duration-100 hover:bg-surface-high/30 ${
        isSelected ? "ring-1 ring-accent-cyan/40 bg-surface-high/20" : ""
      }`}
    >
      <div className="flex items-start justify-between gap-3 mb-2">
        <div className="flex items-center gap-2 flex-wrap">
          <Badge variant={badgeVariant}>{report.source_type}</Badge>
          {report.has_html && (
            <span className="text-[9px] font-mono border border-accent-green/40 text-accent-green px-1.5 py-0.5">
              HTML
            </span>
          )}
        </div>
        <span className="text-[10px] font-mono text-outline shrink-0">
          {report.researched}
        </span>
      </div>

      <h3 className="font-heading text-sm font-bold uppercase leading-tight text-white mb-1">
        {report.title}
      </h3>

      {report.excerpt && (
        <p className="text-[11px] font-mono text-text-secondary/70 line-clamp-2 leading-relaxed">
          {report.excerpt}
        </p>
      )}
    </button>
  );
}

function ReportViewer({ slug }: { slug: string }) {
  const { data, isLoading, error } = useReportContent(slug);

  const handleOpenHtml = useCallback(() => {
    const url = `/api/research/report/${encodeURIComponent(
      // The report/{key} endpoint uses workbench keys, but we can
      // open the HTML directly from the backend
      slug
    )}`;
    window.open(url, "_blank", "noopener,noreferrer");
  }, [slug]);

  if (isLoading) {
    return (
      <div className="p-8 space-y-4">
        {[...Array(12)].map((_, i) => (
          <div
            key={i}
            className="h-3 bg-outline-variant/20 animate-pulse"
            style={{ width: `${60 + Math.random() * 40}%` }}
          />
        ))}
      </div>
    );
  }

  if (error || !data) {
    return (
      <div className="p-8 text-center">
        <p className="font-mono text-sm text-accent-red">
          Failed to load report content.
        </p>
      </div>
    );
  }

  return (
    <div className="flex flex-col h-full min-h-0">
      {/* Toolbar — fixed at top */}
      <div className="shrink-0 flex items-center justify-between border-b border-outline-variant/30 px-6 py-3">
        <span className="font-mono text-[10px] text-outline uppercase tracking-widest">
          {slug}
        </span>
        <GlowButton
          variant="secondary"
          className="py-1.5 px-4 text-[10px]"
          onClick={handleOpenHtml}
        >
          OPEN IN NEW TAB
        </GlowButton>
      </div>

      {/* Markdown content — independently scrollable */}
      <div className="min-h-0 flex-1 overflow-y-auto p-6">
        <div className="prose-research max-w-none">
          <MarkdownRenderer content={data.content} />
        </div>
      </div>
    </div>
  );
}

/** Simple markdown renderer — renders headings, bold, links, lists, code blocks, and tables. */
function MarkdownRenderer({ content }: { content: string }) {
  const lines = content.split("\n");
  const elements: React.ReactNode[] = [];
  let i = 0;

  while (i < lines.length) {
    const line = lines[i];

    // Code blocks
    if (line.startsWith("```")) {
      const codeLines: string[] = [];
      i++;
      while (i < lines.length && !lines[i].startsWith("```")) {
        codeLines.push(lines[i]);
        i++;
      }
      i++; // skip closing ```
      elements.push(
        <pre
          key={elements.length}
          className="bg-bg-base border border-outline-variant/30 p-4 overflow-x-auto my-3"
        >
          <code className="font-mono text-[11px] text-accent-cyan/80">
            {codeLines.join("\n")}
          </code>
        </pre>
      );
      continue;
    }

    // Table rows
    if (line.startsWith("|")) {
      const tableLines: string[] = [];
      while (i < lines.length && lines[i].startsWith("|")) {
        tableLines.push(lines[i]);
        i++;
      }
      elements.push(
        <div key={elements.length} className="overflow-x-auto my-3">
          <table className="w-full border-collapse">
            <tbody>
              {tableLines
                .filter((tl) => !tl.match(/^\|\s*[-:]+/)) // skip separator rows
                .map((tl, ri) => {
                  const cells = tl
                    .split("|")
                    .filter(Boolean)
                    .map((c) => c.trim());
                  const Tag = ri === 0 ? "th" : "td";
                  return (
                    <tr
                      key={ri}
                      className={
                        ri === 0 ? "border-b border-accent-cyan/30" : ""
                      }
                    >
                      {cells.map((cell, ci) => (
                        <Tag
                          key={ci}
                          className={`px-3 py-1.5 text-left font-mono text-[11px] ${
                            ri === 0
                              ? "text-accent-cyan/70 font-bold uppercase tracking-wider text-[10px]"
                              : "text-text-secondary"
                          }`}
                        >
                          <InlineMarkdown text={cell} />
                        </Tag>
                      ))}
                    </tr>
                  );
                })}
            </tbody>
          </table>
        </div>
      );
      continue;
    }

    // Headings
    if (line.startsWith("## ")) {
      elements.push(
        <h2
          key={elements.length}
          className="font-headline font-bold text-base tracking-widest text-accent-cyan uppercase mt-8 mb-3 border-b border-outline-variant/30 pb-1"
        >
          {line.slice(3)}
        </h2>
      );
      i++;
      continue;
    }
    if (line.startsWith("### ")) {
      elements.push(
        <h3
          key={elements.length}
          className="font-headline font-bold text-sm text-white uppercase mt-6 mb-2"
        >
          {line.slice(4)}
        </h3>
      );
      i++;
      continue;
    }
    if (line.startsWith("# ")) {
      elements.push(
        <h1
          key={elements.length}
          className="font-headline font-black text-xl tracking-tighter text-accent-cyan uppercase mb-4"
        >
          {line.slice(2)}
        </h1>
      );
      i++;
      continue;
    }

    // Horizontal rule
    if (line.match(/^---+$/)) {
      elements.push(
        <hr
          key={elements.length}
          className="border-outline-variant/30 my-4"
        />
      );
      i++;
      continue;
    }

    // List items
    if (line.match(/^[-*]\s/)) {
      elements.push(
        <div
          key={elements.length}
          className="flex items-start gap-2 font-mono text-[11px] text-text-secondary leading-relaxed pl-2 my-0.5"
        >
          <span className="mt-1.5 h-1 w-1 shrink-0 bg-accent-cyan" />
          <span>
            <InlineMarkdown text={line.slice(2)} />
          </span>
        </div>
      );
      i++;
      continue;
    }

    // Numbered list
    if (line.match(/^\d+\.\s/)) {
      const num = line.match(/^(\d+)\./)?.[1] ?? "";
      const text = line.replace(/^\d+\.\s/, "");
      elements.push(
        <div
          key={elements.length}
          className="flex items-start gap-2 font-mono text-[11px] text-text-secondary leading-relaxed pl-2 my-0.5"
        >
          <span className="text-accent-cyan/50 shrink-0 w-4 text-right">
            {num}.
          </span>
          <span>
            <InlineMarkdown text={text} />
          </span>
        </div>
      );
      i++;
      continue;
    }

    // Empty line
    if (!line.trim()) {
      elements.push(<div key={elements.length} className="h-2" />);
      i++;
      continue;
    }

    // Regular paragraph
    elements.push(
      <p
        key={elements.length}
        className="font-mono text-[11px] text-text-secondary leading-relaxed my-1"
      >
        <InlineMarkdown text={line} />
      </p>
    );
    i++;
  }

  return <>{elements}</>;
}

/** Render inline markdown: bold, links, inline code */
function InlineMarkdown({ text }: { text: string }) {
  // Process bold, links, and inline code
  const parts: React.ReactNode[] = [];
  let remaining = text;
  let partKey = 0;

  while (remaining.length > 0) {
    // Inline code
    const codeMatch = remaining.match(/^(.*?)`([^`]+)`/);
    if (codeMatch) {
      if (codeMatch[1]) {
        parts.push(
          <BoldAndLinks key={partKey++} text={codeMatch[1]} />
        );
      }
      parts.push(
        <code
          key={partKey++}
          className="bg-bg-base px-1.5 py-0.5 text-accent-cyan/80 text-[10px]"
        >
          {codeMatch[2]}
        </code>
      );
      remaining = remaining.slice(codeMatch[0].length);
      continue;
    }

    // No more inline code — process remaining as bold/links
    parts.push(<BoldAndLinks key={partKey++} text={remaining} />);
    break;
  }

  return <>{parts}</>;
}

function BoldAndLinks({ text }: { text: string }) {
  // Split on bold and links
  const parts: React.ReactNode[] = [];
  let remaining = text;
  let partKey = 0;

  while (remaining.length > 0) {
    // Markdown link [text](url)
    const linkMatch = remaining.match(/^(.*?)\[([^\]]+)\]\(([^)]+)\)/);
    // Bold **text**
    const boldMatch = remaining.match(/^(.*?)\*\*([^*]+)\*\*/);

    const linkIdx = linkMatch ? linkMatch[1].length : Infinity;
    const boldIdx = boldMatch ? boldMatch[1].length : Infinity;

    if (linkIdx < boldIdx && linkMatch) {
      if (linkMatch[1]) parts.push(linkMatch[1]);
      parts.push(
        <a
          key={partKey++}
          href={linkMatch[3]}
          target="_blank"
          rel="noopener noreferrer"
          className="text-accent-cyan hover:underline"
        >
          {linkMatch[2]}
        </a>
      );
      remaining = remaining.slice(linkMatch[0].length);
      continue;
    }

    if (boldIdx < Infinity && boldMatch) {
      if (boldMatch[1]) parts.push(boldMatch[1]);
      parts.push(
        <strong key={partKey++} className="text-white font-bold">
          {boldMatch[2]}
        </strong>
      );
      remaining = remaining.slice(boldMatch[0].length);
      continue;
    }

    parts.push(remaining);
    break;
  }

  return <>{parts}</>;
}

/**
 * Reports page — browse all generated research reports.
 * Master-detail layout: report list on left, content viewer on right.
 */
export default function ReportsPage() {
  const { data: reports, isLoading, error } = useReports();
  const [selectedSlug, setSelectedSlug] = useState<string | null>(null);
  const reduceMotion = useReducedMotion();

  const handleSelect = useCallback((slug: string) => {
    setSelectedSlug((prev) => (prev === slug ? null : slug));
  }, []);

  return (
    <div className="pb-8">
      {/* Page header */}
      <div className="mb-10 flex flex-col gap-4 md:flex-row md:items-end md:justify-between">
        <div>
          <h1 className="flex items-baseline gap-3 font-heading text-4xl font-black uppercase tracking-tighter text-accent-cyan">
            Reports
            <span className="text-sm font-mono font-normal text-text-muted">
              /Research_Library
            </span>
          </h1>
          <p className="mt-1 font-mono text-xs uppercase text-text-muted">
            Generated Research Reports
          </p>
        </div>
        {reports && (
          <span className="font-mono text-[10px] text-outline uppercase">
            {reports.length} REPORTS
          </span>
        )}
      </div>

      {/* Error state */}
      {error && (
        <div className="mb-6 border border-accent-red/30 bg-accent-red/5 p-4 font-mono text-xs text-accent-red">
          Failed to load reports. Check API connection.
        </div>
      )}

      {/* Loading skeleton */}
      {isLoading && (
        <div className="space-y-3">
          {[...Array(6)].map((_, i) => (
            <div
              key={i}
              className="h-20 bg-bg-surface border-l-4 border-outline-variant/20 animate-pulse"
            />
          ))}
        </div>
      )}

      {/* Empty state */}
      {!isLoading && !error && reports?.length === 0 && (
        <div className="border border-outline-variant/30 bg-bg-surface p-8 text-center">
          <p className="font-mono text-sm text-text-secondary mb-2">
            NO REPORTS GENERATED
          </p>
          <p className="font-mono text-xs text-text-muted">
            Research reports appear here after completing workbench items.
          </p>
        </div>
      )}

      {/* Master-detail layout */}
      {!isLoading && reports && reports.length > 0 && (
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
            {/* Report list — independently scrollable */}
            <div
              className={`${
                selectedSlug
                  ? "lg:col-span-4 lg:sticky lg:top-20 lg:max-h-[calc(100vh-120px)] lg:overflow-y-auto"
                  : "lg:col-span-12"
              }`}
            >
              <div className="space-y-2">
                {reports.map((report) => (
                  <ReportCard
                    key={report.slug}
                    report={report}
                    isSelected={selectedSlug === report.slug}
                    onSelect={handleSelect}
                  />
                ))}
              </div>
            </div>

            {/* Content viewer */}
            <AnimatePresence>
              {selectedSlug && (
                <m.div
                  initial={{ opacity: 0, x: reduceMotion ? 0 : 20 }}
                  animate={{ opacity: 1, x: 0 }}
                  exit={{ opacity: 0, x: reduceMotion ? 0 : 20 }}
                  transition={reduceMotion ? { duration: 0 } : { type: "spring", stiffness: 300, damping: 30 }}
                  className="lg:col-span-8 bg-bg-surface border border-outline-variant/30 lg:sticky lg:top-20 h-[calc(100vh-120px)] flex flex-col overflow-hidden"
                >
                  <ReportViewer slug={selectedSlug} />
                </m.div>
              )}
            </AnimatePresence>
          </div>
      )}
    </div>
  );
}

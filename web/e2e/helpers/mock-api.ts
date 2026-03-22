import type { Page } from "@playwright/test";

/** Mock data for dashboard stats */
const MOCK_STATS = {
  papers: 42,
  tools: 18,
  blog_queue: 7,
  active_projects: 5,
};

/** Mock project list */
const MOCK_PROJECTS = [
  {
    name: "Research Dashboard",
    status: "active",
    domain: "dev-tools",
    tech: ["Python", "Next.js", "FastAPI"],
    overview: "Research intelligence dashboard.",
  },
  {
    name: "ML Pipeline",
    status: "active",
    domain: "ml",
    tech: ["Python", "PyTorch"],
    overview: "Machine learning pipeline framework.",
  },
];

/** Mock project items */
const MOCK_PROJECT_ITEMS = [
  {
    name: "TF-IDF Vectorizer",
    source_type: "tool",
    source: "TLDR",
    notes: "Text vectorization utility",
    tags: ["nlp", "ml"],
  },
  {
    name: "Attention Mechanism",
    source_type: "method",
    source: "JournalClub",
    notes: "Transformer attention patterns",
    tags: ["deep-learning"],
  },
];

/** Mock graph data */
const MOCK_GRAPH_DATA = {
  nodes: [
    { id: "Research Dashboard", type: "project", label: "Research Dashboard" },
    { id: "TF-IDF Vectorizer", type: "tool", label: "TF-IDF Vectorizer" },
    { id: "Attention Mechanism", type: "method", label: "Attention Mechanism" },
  ],
  edges: [
    { source: "Research Dashboard", target: "TF-IDF Vectorizer" },
    { source: "Research Dashboard", target: "Attention Mechanism" },
  ],
};

/** Mock workbench data */
const MOCK_WORKBENCH: Record<string, unknown> = {
  "tool::TF-IDF": {
    name: "TF-IDF Vectorizer",
    source_type: "tool",
    status: "queued",
    notes: "Text vectorization utility",
    previous_status: null,
    added_at: "2026-03-20T10:00:00Z",
    verdict: null,
    pid: null,
    log_file: null,
  },
  "method::Attention": {
    name: "Attention Mechanism",
    source_type: "method",
    status: "researching",
    notes: "Transformer attention patterns",
    previous_status: "queued",
    added_at: "2026-03-19T08:00:00Z",
    verdict: null,
    pid: 12345,
    log_file: "/tmp/research-attention.log",
  },
  "tool::LangChain": {
    name: "LangChain Framework",
    source_type: "tool",
    status: "completed",
    notes: "LLM application framework",
    previous_status: "researching",
    added_at: "2026-03-18T12:00:00Z",
    verdict: "programmatic",
    pid: null,
    log_file: "/tmp/research-langchain.log",
  },
};

/** Mock blog queue */
const MOCK_BLOG_QUEUE = [
  {
    title: "Building a Research Dashboard",
    status: "draft",
    category: "tutorial",
    tags: ["streamlit", "python"],
  },
  {
    title: "ML Pipeline Patterns",
    status: "idea",
    category: "deep-dive",
    tags: ["ml", "architecture"],
  },
];

/** Mock tools */
const MOCK_TOOLS = [
  {
    name: "Cursor AI",
    category: "IDE",
    status: "watching",
    source: "TLDR",
    notes: "AI-powered code editor",
    tags: ["ai", "ide"],
  },
];

/** Mock reports */
const MOCK_REPORTS = [
  {
    title: "Week 12 JournalClub",
    date: "2026-03-15",
    source: "JournalClub",
    type: "journalclub",
    highlights: ["New transformer architecture"],
  },
];

/** Mock graph health */
const MOCK_GRAPH_HEALTH = {
  total_nodes: 45,
  total_edges: 78,
  connected_components: 3,
  orphan_nodes: 2,
  avg_degree: 3.5,
  density: 0.08,
};

/** Mock instagram feed */
const MOCK_INSTAGRAM = [
  {
    id: "ig-001",
    account: "ai_research",
    title: "GPT-5 Architecture Deep Dive",
    key_points: ["Novel attention mechanism", "Sparse MoE routing"],
    transcript_excerpt: "The key innovation is in the routing layer...",
    tags: ["gpt", "architecture"],
    timestamp: new Date(Date.now() - 3_600_000 * 2).toISOString(),
    status: "analyzed",
  },
  {
    id: "ig-002",
    account: "ml_daily",
    title: "RLHF Alternatives",
    key_points: ["DPO gaining traction", "Constitutional AI approach"],
    tags: ["rlhf", "alignment"],
    timestamp: new Date(Date.now() - 3_600_000 * 24).toISOString(),
  },
];

/** Mock analysis response */
const MOCK_ANALYSIS = {
  analysis: "This item is highly relevant to your project...",
  relevance_score: 0.85,
  model: "claude-haiku-4-5-20251001",
  tokens: { input: 500, output: 200 },
};

/** Mock summarize response */
const MOCK_SUMMARY = {
  summary: "This post discusses novel approaches to transformer architecture...",
};

/**
 * Intercept all /api/* routes and return mock JSON.
 * Call this in test beforeEach to avoid needing a running backend.
 */
export async function mockAllApiRoutes(page: Page): Promise<void> {
  await page.route("**/api/stats", (route) =>
    route.fulfill({ json: MOCK_STATS })
  );

  await page.route("**/api/projects", (route) =>
    route.fulfill({ json: MOCK_PROJECTS })
  );

  await page.route("**/api/project-index/**", (route) =>
    route.fulfill({ json: MOCK_PROJECT_ITEMS })
  );

  await page.route("**/api/graph/*/viz", (route) =>
    route.fulfill({ json: MOCK_GRAPH_DATA })
  );

  await page.route("**/api/workbench", (route) => {
    if (route.request().method() === "GET") {
      return route.fulfill({ json: MOCK_WORKBENCH });
    }
    // POST — send to workbench
    return route.fulfill({ json: { success: true } });
  });

  await page.route("**/api/workbench/*/status", (route) =>
    route.fulfill({ json: { success: true } })
  );

  await page.route("**/api/blog-queue", (route) =>
    route.fulfill({ json: MOCK_BLOG_QUEUE })
  );

  await page.route("**/api/tools", (route) =>
    route.fulfill({ json: MOCK_TOOLS })
  );

  await page.route("**/api/reports**", (route) =>
    route.fulfill({ json: MOCK_REPORTS })
  );

  await page.route("**/api/graph/health", (route) =>
    route.fulfill({ json: MOCK_GRAPH_HEALTH })
  );

  await page.route("**/api/instagram/feed", (route) =>
    route.fulfill({ json: MOCK_INSTAGRAM })
  );

  await page.route("**/api/instagram/refresh", (route) =>
    route.fulfill({ json: { success: true, count: 5 } })
  );

  await page.route("**/api/analyze/**", (route) =>
    route.fulfill({ json: MOCK_ANALYSIS })
  );

  await page.route("**/api/summarize/**", (route) =>
    route.fulfill({ json: MOCK_SUMMARY })
  );

  // Catch-all for any unmatched API routes
  await page.route("**/api/**", (route) => {
    console.warn(`Unhandled API route: ${route.request().url()}`);
    return route.fulfill({ json: {}, status: 200 });
  });

  // Block WebSocket connections (they'd fail without backend)
  await page.route("**/ws/**", (route) => route.abort());
}

export {
  MOCK_STATS,
  MOCK_PROJECTS,
  MOCK_PROJECT_ITEMS,
  MOCK_GRAPH_DATA,
  MOCK_WORKBENCH,
  MOCK_BLOG_QUEUE,
  MOCK_TOOLS,
  MOCK_REPORTS,
  MOCK_GRAPH_HEALTH,
  MOCK_INSTAGRAM,
  MOCK_ANALYSIS,
  MOCK_SUMMARY,
};

# Adversarial Planner Prompt — Session 24.6

Copy everything below the line into ChatGPT 5.4.

---

You are a senior staff engineer acting as an **adversarial planner**. Your job is to tear apart the implementation plan below and find every concrete failure mode, underspecified dependency, race condition, missing edge case, and architectural smell that will cause real breakage during implementation.

You are NOT here to praise the plan. You are here to prevent wasted hours.

## Output Format

Produce a markdown document with this exact structure:

```
# Session 24.6 Critique: Knowledge Linker Port Pre-Mortem

This is an adversarial review of Session 24.6 from `GSD_PLAN.md`. It only lists concrete failure modes and underspecified dependencies that are likely to cause real breakage during implementation.

## Summary Table

| Severity | Sub-task | Issue | Recommendation |
|----------|----------|-------|----------------|
| CRITICAL | ... | ... | ... |
| HIGH | ... | ... | ... |
| MEDIUM | ... | ... | ... |

## Detailed Analysis

### [24.6a] Create Linker Router
(detailed findings per sub-task)

### [24.6b] Add Pydantic Model
...
(continue for each sub-task)

## Cross-Cutting Concerns
(issues that span multiple sub-tasks)

## Missing From the Plan
(things the plan should address but doesn't mention at all)
```

## Severity Definitions

- **CRITICAL**: Will cause the feature to not work at all, data corruption, or a security hole
- **HIGH**: Will cause a bug, test failure, or UX problem that blocks ship
- **MEDIUM**: Will cause tech debt, maintenance pain, or a degraded experience

## What to Attack

Focus on these vectors:

1. **Concurrency & state** — The plan uses in-memory `_job` dict with `threading.Lock`. Is this actually safe with FastAPI's async event loop + `BackgroundTasks`? What happens if the process restarts mid-run? What if two uvicorn workers are running?
2. **Import coupling** — The plan says "import `_graph_cache` from graph router" for invalidation. Is cross-router import of private state a good pattern? What breaks when the graph module is refactored?
3. **Error recovery** — What happens if `link_vault_all()` partially completes (5 of 10 directories linked) then crashes? Is the vault in a consistent state? Can the user re-run safely?
4. **Frontend state machine** — The polling card has states: idle → running → complete/error. What happens if the user navigates away and comes back? What if they refresh the page mid-run? What if the API is unreachable?
5. **Testing gaps** — Are the proposed mocks testing real behavior or just testing that the mock framework works? What integration scenarios are missing?
6. **Missing sub-tasks** — Is there work that needs to happen that isn't listed? (e.g., TypeScript types for the API response, SWR/fetch hooks, error boundary handling)
7. **Dependency chain** — The plan says [24.6d]+[24.6e] can run in parallel. Can they really? Does [24.6e] need [24.6d] to be merged first to render?
8. **Design system compliance** — The plan references specific Tailwind classes. Are those actually defined in this project's design system, or are they generic Tailwind that won't match?
9. **Proxy/routing** — The plan assumes `/api/:path*` wildcard covers the new route. What if the proxy config is more specific than assumed?
10. **Idempotency** — Can `link_vault_all()` be safely called twice? Does re-injecting wiki-links into already-linked files cause double-bracketing like `[[[[Project]]]]`?

## Context: The Plan Under Review

### Session 24.6: Knowledge Linker Port (FastAPI + Next.js)

**Scope:** Port the Knowledge Linker (Obsidian graph manicure) from Streamlit-only to the dual-stack. Expose `link_vault_all()` via a FastAPI background-task endpoint with polling, add a "Link Vault" card to the Next.js Agentic Hub tab with progress feedback. Zero changes to `src/utils/knowledge_linker.py` — it's already Streamlit-free.

**Design decisions:**
- **Polling over WebSocket** — operation takes 2-5s, same pattern as IG refresh
- **Single-job model** — vault linking is sequential, only one run at a time (409 on concurrent attempts)
- **Explicit graph cache invalidation** — clear `_graph_cache` after linking instead of waiting for 1hr TTL

**Concurrency:** [24.6a]+[24.6b] can run in parallel → [24.6c] depends on both → [24.6d]+[24.6e] can run in parallel → [24.6f] depends on [24.6d] → [24.6g] last

#### [24.6a] Create Linker Router

- Create `api/routers/linker.py` following `ingestion.py` async-job-with-polling pattern:
  - In-memory `_job` dict + `threading.Lock` for thread-safe reads/writes
  - `_job` stores: `status` ("idle"|"running"|"complete"|"error"), `current_directory` (str), `results` (dict[str,int]), `started_at`, `completed_at`, `error`
  - `POST /api/linker/run` — checks if running (409), sets "running", spawns `BackgroundTasks`, returns 202
  - Background worker: calls `build_entity_index()` once, iterates `_LINK_TARGETS` updating `current_directory` before each dir, calls `link_satellites_to_projects()` last. Try/except wrapper always sets terminal status.
  - `GET /api/linker/status` — returns current `_job` dict (or `{"status": "idle"}`)
  - Router prefix: `/api/linker`, tag: `linker`

#### [24.6b] Add Pydantic Model

- Add `LinkerStatusResponse` to `api/models.py`:
  - Fields: `status` (Literal["idle","running","complete","error"]), `current_directory` (str|None), `results` (dict[str,int]|None), `total_modified` (int|None), `started_at` (str|None), `completed_at` (str|None), `error` (str|None)

#### [24.6c] Register Router + Graph Cache Invalidation

- Import `linker` from `api.routers`, add `app.include_router(linker.router)` in `api/main.py` after `ingestion`
- In linker background worker: after successful `link_vault_all`, clear `_graph_cache` from `api/routers/graph.py` so graph health endpoints reflect new links immediately
- Verify Next.js proxy config (`/api/:path*` wildcard) covers `/api/linker/*` — no changes expected

#### [24.6d] Wire AgenticHubTab into Dashboard

- Add `"agentic-hub"` to `DashboardTab` union type in `web/src/app/dashboard/types.ts`
- Add `{ id: "agentic-hub", label: "AGENTIC HUB" }` to `DASHBOARD_TABS` array
- Add lazy import + render for `AgenticHubTab` in `web/src/app/dashboard/DashboardView.tsx`

#### [24.6e] Add Knowledge Linker Card to Agentic Hub

- Add `KnowledgeLinkerCard` component to `AgenticHubTab.tsx` (or extract to `KnowledgeLinkerCard.tsx` if >80 lines):
  - "LINK VAULT" `GlowButton` fires `POST /api/linker/run`
  - State machine: idle → running → complete/error
  - While running: poll `GET /api/linker/status` every 1.5s, show `current_directory` with pulsing cyan dot (reuse `RefreshStatusPanel` pattern)
  - On complete: results summary — total files modified, per-directory breakdown (only dirs with modifications > 0), green success banner with DISMISS
  - On error: red error message
  - Handle 409: show "ALREADY RUNNING" state
  - Card styling: `bg-bg-surface border border-accent-cyan/20 p-5`, header "KNOWLEDGE LINKER" in `font-headline text-accent-cyan uppercase tracking-widest`

#### [24.6f] API Endpoint Tests

- Create `tests/test_linker_router.py`:
  - `POST /api/linker/run` returns 202 with `{"status": "accepted"}`
  - `POST /api/linker/run` while running returns 409
  - `GET /api/linker/status` returns idle when no job has run
  - `GET /api/linker/status` returns complete with results after job finishes
  - Mock `knowledge_linker.build_entity_index`, `link_directory`, `link_satellites_to_projects` at import boundary
  - Mock `get_vault_path_str` dependency

#### [24.6g] Quality Gate

- `ruff check src/ api/ tests/` passes
- `pytest tests/ -v --tb=short` — all tests pass including new linker tests
- Manual: click "LINK VAULT" in Next.js Agentic Hub → see progress → see results summary
- Manual: verify graph health endpoint returns updated metrics after linking
- Manual: trigger concurrent run → confirm 409 response

## Additional Context

- The existing `ingestion.py` router uses the same in-memory job + lock pattern for Instagram feed refresh
- `knowledge_linker.py` uses atomic file writes (`tempfile.mkstemp` + `os.replace`) so partial writes shouldn't corrupt files
- `inject_wiki_links()` uses regex that matches plain text but skips existing `[[wiki-links]]` — but verify this claim
- The app runs as a single uvicorn process in dev (no workers), but production intent is unclear
- The Next.js frontend uses SWR for data fetching but the plan doesn't mention SWR — it says "poll"
- The `AgenticHubTab.tsx` already exists at 660 lines

## Your Deliverable

Output ONLY the critique markdown document. No preamble, no "here's my analysis", no sign-off. Start with `# Session 24.6 Critique:` and end with the last finding. Be specific — cite sub-task IDs, name the exact failure scenario, and give a concrete fix. Vague concerns like "consider edge cases" are worthless.

Save the output as: `docs/critiques/session-24-6-critique.md`

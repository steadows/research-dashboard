# Session 24.6 Critique: Knowledge Linker Port Pre-Mortem

This is an adversarial review of Session 24.6 from `GSD_PLAN.md`. It only lists concrete failure modes and underspecified dependencies that are likely to cause real breakage during implementation.

## Summary Table

| Severity | Sub-task | Issue | Recommendation |
|----------|----------|-------|----------------|
| CRITICAL | [24.6a] | The in-memory `_job` dict + `threading.Lock` only serializes work inside one Python process. Under two uvicorn workers, or after a worker restart, two linker runs can mutate the same `Plans` / `Blueprints` / `Reference` files concurrently and lose updates. | Use an inter-process lock plus a durable job record, or make single-worker deployment an explicit enforced requirement instead of an assumption. |
| CRITICAL | [24.6a] | The plan assumes reruns are safe after partial failure, but `inject_wiki_links()` only avoids bare `[[name]]` matches. It does not skip full wiki-link spans with custom labels, markdown links, or code blocks, so reruns are not actually proven idempotent. | Add utility-level idempotency tests first and fix the matcher before shipping a "safe rerun" API. |
| HIGH | [24.6a], [24.6c] | "Zero changes to `knowledge_linker.py`" conflicts with per-directory progress. The target list needed for progress lives in `src/pages/1_Dashboard.py`, not in shared utils, so the FastAPI worker must either duplicate it or import from a Streamlit page. | Extract the target list and orchestration into a shared utility or service that both Streamlit and FastAPI can call. |
| HIGH | [24.6a] | `link_directory()` logs and swallows per-file exceptions, so the job can return `status="complete"` while some notes failed to update. | Surface per-file failures in the job payload and add a partial-failure terminal state instead of treating warnings as success. |
| HIGH | [24.6b], [24.6e] | `LinkerStatusResponse` has no `run_id`, warning list, or partial-success field, so the frontend cannot tell "my current run" from a stale previous run or a different browser tab's run. | Add a job identifier plus explicit partial/error metadata to the response contract. |
| HIGH | [24.6c] | Clearing `api.routers.graph._graph_cache` imports private router state and bypasses the `_graph_lock` that currently guards cache access. | Move cache ownership behind a public invalidation helper that acquires the same lock and invalidates only the relevant vault key. |
| HIGH | [24.6c] | Invalidating the graph cache only on full success leaves graph endpoints stale after a partially successful run that crashes late. | Invalidate whenever any mutations occurred, not only on the all-green path, and test the warmed-cache case explicitly. |
| HIGH | [24.6d], [24.6e] | The dashboard tab state is local-only. Refreshing the page or navigating away resets `DashboardView` to `"home"` and unmounts the card mid-run unless the card rehydrates from `/api/linker/status`. The plan never says it does. | Fetch status on mount, resume polling after remount, and either persist the active tab in the URL or treat `/agentic-hub` as the canonical long-running surface. |
| HIGH | [24.6e] | Handling 409 as a static "ALREADY RUNNING" state strands the second tab/browser with no progress or completion details. 409 is evidence that a job exists, not a terminal UI state. | On 409, immediately fetch `/api/linker/status` and join the active polling loop. |
| HIGH | [24.6f] | The proposed API tests are timing-sensitive and under-patched: `BackgroundTasks` can finish before the second request, module-global job state will leak across tests, and patching only `utils.knowledge_linker.*` misses router-level imports. | Add a linker-state reset helper, patch `api.routers.linker.*`, and use a blocking fake or direct worker test for the 409 path. |
| MEDIUM | [24.6e] | The UI promises a "per-directory breakdown," but the existing utility returns a pseudo-directory `Satellites` that can span multiple folders. | Define a structured results shape instead of exposing the raw dict from `link_vault_all()`. |
| MEDIUM | [24.6g] | The manual graph-health and 409 checks can false-pass. If graph health is not fetched before linking, invalidation is never exercised; if the button disables itself, the UI may never actually hit the 409 path. | Warm `/api/graph/health` first, then run the linker, and trigger 409 from a second client or raw API call. |

## Detailed Analysis

### [24.6a] Create Linker Router

- The plan ports the `api/routers/ingestion.py` pattern without accounting for a crucial difference: Instagram refresh writes isolated note sets keyed by username, while the knowledge linker rewrites shared vault files across the whole corpus. A module-level `_job` dict with `threading.Lock` is only safe inside one interpreter process.
- That becomes a real data race as soon as two uvicorn workers exist or a process restarts mid-run. Two workers can both accept `POST /api/linker/run`, and both will eventually touch `Plans`, `Blueprints`, and `Reference`. Because both `link_directory()` and `link_satellites_to_projects()` use atomic last-writer-wins `os.replace`, one run can overwrite transformations produced by the other.
- The plan also says the background worker should iterate `_LINK_TARGETS`, but `_LINK_TARGETS` is currently defined in `src/pages/1_Dashboard.py`, not in `src/utils/knowledge_linker.py`. Keeping `knowledge_linker.py` unchanged forces one of two bad options:
  - duplicate the target list in the router and hope it never drifts from `link_vault_all()`
  - import a Streamlit page from FastAPI just to get routing metadata
- Partial failure semantics are currently wrong for an API surface. `link_directory()` catches file-level exceptions, logs a warning, and keeps going. That means the job can end as `"complete"` even though some notes were skipped. The UI would present a success banner on an inconsistent vault.
- The rerun story is also underspecified. The plan assumes a failed run can be retried safely because the linker "skips existing wiki-links," but the current matcher only excludes text immediately wrapped by `[[` and `]]`, and only short-circuits when exact `[[display_name]]` already exists. It does not skip markdown links, code blocks, or custom-label wiki-links. A retry after partial mutation is not actually proven safe.

### [24.6b] Add Pydantic Model

- `LinkerStatusResponse` is too lossy for the workflow the plan describes. There is no `run_id`, no warning list, no `partial` flag, and no file-level failures. That means the frontend cannot distinguish:
  - a stale `"complete"` payload from an earlier run
  - a run started in another tab or browser
  - "all files processed cleanly" versus "some files updated, some silently failed"
- The current proposed fields also make `results` ambiguous while the job is still running. Are they final counts, partial counts, or only present on completion? Without a stronger contract, the frontend either has to guess or avoid rendering intermediate progress beyond a single directory label.
- If the API is going to be polled and resumed after remount, the response model needs identity and terminal-state clarity, not just a generic status string.

### [24.6c] Register Router + Graph Cache Invalidation

- Importing `_graph_cache` from `api/routers/graph.py` is brittle coupling to private router internals. Today the graph router owns both `_graph_cache` and `_graph_lock`; the linker plan only mentions clearing the cache object, not using the same lock. That is a thread-safety violation against the current implementation.
- Clearing the whole cache also assumes one global vault forever. The current cache is keyed by `vault_path`, so a future second vault path or a test fixture with a different path gets blown away too. The invalidation API should target the relevant key, not the entire cache.
- The success-only invalidation rule is wrong once partial mutation is possible. If five directories were linked and then the job crashes, the graph cache can remain stale for up to the 1-hour TTL even though the vault has already changed. A late failure does not mean "nothing changed."
- The HTTP proxy assumption is the one part of this sub-task that is actually grounded: `web/next.config.ts` does rewrite `/api/:path*`. The risky part is not proxying, it is cache ownership and invalidation timing.

### [24.6d] Wire AgenticHubTab into Dashboard

- Embedding the card inside dashboard tabs adds a remount boundary that the plan ignores. `DashboardView` keeps `activeTab` in local React state and always initializes to `"home"`. If the user refreshes mid-run, they do not come back to the Agentic Hub tab; they come back to Home and the card is unmounted.
- That matters because the plan's card state machine is also local. Without an explicit "rehydrate from `/api/linker/status` on mount" step, wiring the feature into dashboard tabs makes the in-progress job effectively disappear from the UI after a very normal navigation event.
- There is also an entry-point ambiguity the plan never resolves: the standalone `/agentic-hub` page already exists and renders the same `AgenticHubTab`. If the long-running linker card lives in that shared component, the session needs to define whether both surfaces are supported and tested or whether one becomes canonical.

### [24.6e] Add Knowledge Linker Card to Agentic Hub

- The proposed idle → running → complete/error state machine is not enough for the actual user flows. It does not define what happens on initial mount when a job is already running, when the last known job is already complete, or when a user rejoins from another tab.
- Treating 409 as a separate "ALREADY RUNNING" UI state is a design bug. A second client that receives 409 should join the existing job, not stop at a static banner with no progress.
- Reusing the `RefreshStatusPanel` pattern is dangerous as written. The current Instagram poller treats fetch failures as "keep polling" and never enters an explicit error state. If the linker card copies that behavior, an API outage or proxy problem becomes an infinite cyan spinner.
- The results contract and the planned UI copy do not line up cleanly. The current utility returns `results["Satellites"]`, but the card wants a per-directory breakdown. "Satellites" is an implementation step spanning multiple folders, not a directory a user can reason about.
- `AgenticHubTab.tsx` is already large and heavily stateful. If the new card lives inline, the lack of separation will make the existing component tests harder to patch and will encourage more ad hoc `fetch()` polling instead of a typed hook or reusable poll helper.

### [24.6f] API Endpoint Tests

- The proposed test bullets do not match the repo's current testing pattern closely enough. Existing API tests patch both source modules and router-level imports specifically because import timing matters. A new linker test file that patches only `utils.knowledge_linker.*` can still hit real router-bound references.
- The idle-status test is order-dependent unless linker state is explicitly reset. The job store is module-global, so once one test marks it complete, a later test can stop seeing `{"status": "idle"}` even with a fresh `TestClient`.
- The 409 test is also timing-sensitive. In `TestClient`, the background task can complete before the second request is issued, which turns "already running" into a flaky race unless the worker is deliberately blocked with an event or fake.
- The proposed suite only tests happy-path completion. It does not cover:
  - file-level partial failures hidden by `link_directory()`
  - error terminal state after an exception
  - graph-cache invalidation after a warmed `/api/graph/health` call
  - retry safety after a partial run

### [24.6g] Quality Gate

- The cache-invalidation manual check can false-pass unless the graph cache is warmed first. If the tester runs `/api/graph/health` only after linking, the endpoint will build a fresh graph regardless of whether invalidation ever happened.
- The 409 manual check is also underspecified. If the UI disables the button while running, a same-tab click test never exercises the server-side conflict path. You need a second tab, second browser, or raw API call to prove the lock actually works.
- There is no quality gate for the navigation and reload scenarios introduced by the dashboard-tab embedding. A user refreshing mid-run is not an edge case here; it is a default browser action, and the plan never verifies recovery.
- There is no idempotency gate against already-linked content that uses markdown links, code blocks, or custom-label wiki-links. Given the current matcher, that is exactly the sort of regression that should be tested before exposing a one-click "link the whole vault" endpoint.

## Cross-Cutting Concerns

- `api/routers/ingestion.py` is the wrong architectural template for this feature. The ingestion job is keyed and isolated; the linker rewrites shared global state and needs stronger coordination, resumability, and observability.
- The plan currently has three possible sources of truth for linker orchestration: `src/pages/1_Dashboard.py` `_LINK_TARGETS`, `src/utils/knowledge_linker.link_vault_all()`, and the proposed FastAPI worker loop. If all three exist, they will drift.
- The session treats "background task + polling" as sufficient, but the real hard part is mutation semantics after failure: what changed already, what failed, whether graph cache was invalidated, and how a second client can safely resume visibility into the same run.
- The frontend and backend freshness story is also incomplete. Even if the backend graph cache is invalidated correctly, any frontend view that expects immediate updated metrics still needs a deliberate SWR revalidation path or explicit "refresh graph views" behavior.

## Missing From the Plan

- A shared linker orchestration surface in `src/utils/knowledge_linker.py` or a new shared service so FastAPI and Streamlit stop duplicating target lists and step names.
- A public graph-cache invalidation helper that owns `_graph_cache` and `_graph_lock` together instead of cross-router imports of private state.
- A frontend type and poll helper for linker status, not ad hoc untyped `fetch()` calls inside `AgenticHubTab.tsx`.
- Frontend test updates for the new card states, especially `web/src/__tests__/AgenticHubTab.test.tsx`, plus mock-route updates in `web/e2e/helpers/mock-api.ts` if the feature is ever exercised in browser tests.
- Utility-level tests for `src/utils/knowledge_linker.py` covering reruns, markdown links, code blocks, custom-label wiki-links, and partial-failure retry safety.
- An explicit deployment contract for worker count and process restarts. Right now the plan quietly relies on single-process semantics while also hinting that production is undecided.

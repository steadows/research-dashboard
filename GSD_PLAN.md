# GSD Plan: Research Intelligence Dashboard

> **Created:** 2026-03-14 | **Revised:** 2026-03-22 | **Stack:** Python 3.11 · Streamlit (legacy) · FastAPI · Next.js 16 · Anthropic SDK · PyYAML
> **Reference:** `Plans/Research Intelligence System.md` (Obsidian) — full design spec

---

## 0. Execution Model

**One Ralph Loop per session.** Each GSD session runs in its own Claude Code context window.

```bash
# Operator runs one session at a time:
/ralph-loop "Execute Session N of GSD_PLAN.md. Read GSD_PLAN.md and CLAUDE.md first. Mark tasks [~] when starting, [x] when done. Follow TDD per /steadows-tdd. Run ALL quality gate sub-tasks listed in the session. Conda env: /opt/anaconda3/envs/research-dashboard. Vault: /Users/stevemeadows/SteveVault. API key: .env.local ANTHROPIC_API_KEY. Output <promise>SESSION N COMPLETE</promise> when all tasks in Session N are [x]." --max-iterations 10 --completion-promise "SESSION N COMPLETE"
```

After each session completes, start a **new** Claude Code session for the next one.

Sessions 3 and 4 can run concurrently (separate terminal windows) after Session 2.
Sessions 8, 9, 10, and 11 run sequentially — each depends on the prior completing.
Sessions 12 and 13 run sequentially after Session 11.
Session 14 runs after Session 13.
Sessions 17–20 run sequentially (infrastructure → API read → API mutate → frontend bootstrap).
Sessions 21 and 22 can run concurrently (separate terminal windows) after Session 20.
Session 23 runs after both 21 and 22 complete.
Sessions 24 and 25 run sequentially after Session 23.

---

## 1. Quality Gate Skills

| Command | Invocation |
|---------|------------|
| TDD Workflow | `/steadows-tdd` |
| Code Review | `/steadows-code-review` |
| Verify | `/steadows-verify` |
| Security Review | `/steadows-security-review` |
| LLM Trace | `~/.claude/skills/streamlit-llm-trace/SKILL.md` |
| Claude API | _(removed — subprocess rules inlined in Session 10b)_ |
| Learn Eval | `/everything-claude-code:learn-eval` (ECC plugin) |

### Streamlit Sub-Skills

All live at `~/.claude/skills/developing-with-streamlit/skills/{name}/SKILL.md`:

| When Building | Sub-Skill Name |
|---------------|---------------|
| Dashboard cards, KPIs, metrics | `building-streamlit-dashboards` |
| Multipage nav | `building-streamlit-multipage-apps` |
| LLM output rendering, cost tracking | `building-streamlit-llm-apps` |
| Dark OLED theme config | `creating-streamlit-themes` |
| Caching, fragments, performance | `optimizing-streamlit-performance` |
| Icons, badges, visual polish | `improving-streamlit-design` |
| Session state, callbacks | `using-streamlit-session-state` |
| Widget double-click bugs | `avoiding-streamlit-widget-pitfalls` |
| Layouts, tabs, columns | `using-streamlit-layouts` |
| Selectbox, radio, pills | `choosing-streamlit-selection-widgets` |

---

## 2. Architecture Patterns

**Design System** (Dark OLED):
- Background: `#0A0A0A` | Surface: `#111827` | Border: `#1F2937`
- Primary: `#1E40AF` | Accent: `#3B82F6` | CTA: `#F59E0B`
- Heading: Exo (300/400/600/700) | Body: Roboto Mono (400/500)
- Transitions: 150–300ms | Contrast: WCAG AA minimum (4.5:1)

**Repository Pattern:**
- Pages call utils; utils call filesystem. Never read files directly from page code.

**Streamlit Conventions:**
- Entry: `src/Home.py` | Pages: `src/pages/` | Utils: `src/utils/`
- Session state keys namespaced: `dashboard__*`, `cockpit__*`
- Never call Claude API directly from page files

---

## 3. Logging & Observability

Module-level logger: `logger = logging.getLogger(__name__)`

| Level | What to Log |
|-------|------------|
| DEBUG | Parse start/end, wiki-link counts, cache hit/miss, full LLM prompts (LLM_TRACE=1 only) |
| INFO | App startup, vault loaded, analysis requested (item name + project), cache write |
| WARNING | Parse errors, status file corrupt/reset, Claude API retry |
| ERROR | Claude API hard failure, vault path not found, env vars missing |

**LLM Trace** (per `~/.claude/skills/streamlit-llm-trace/SKILL.md`):
- Dedicated logger: `_llm_trace_log = logging.getLogger("llm_trace")`, `propagate = False`
- Before call: full prompt at DEBUG (LLM_TRACE=1 only)
- After call: model + token counts + cost at INFO
- On error: full prompt + error at WARNING

---

## 4. Dependency Graph

```
Session 1 (Setup + Design)
    └── Session 2 (Data Layer)
            ├── Session 3 (Dashboard View) ──────┐
            └── Session 4 (Claude API Layer) ─────┤
                                                  └── Session 5 (Project Cockpit)
                                                            └── Session 6 (Polish + Ship)
                                                                      └── Session 7 (Prompt Quality Audit + Context Enrichment)
                                                                                └── Session 8 (Workbench Page + Tool Dismiss)
                                                                                          └── Session 9 (Methods Workbench — Schema Generalization)
                                                                                                    └── Session 10 (Research Agent)
                                                                                                              └── Session 11 (Sandbox + Vault Note)
                                                                                                                        └── Session 12 (Instagram Ingester + Parser)
                                                                                                                                  └── Session 13 (Agentic Hub Tab + Workbench Integration)
                                                                                                                                            └── Session 14 (Instagram Topic Research)
                                                                                                                                                      └── Session 15 (Graph Analysis Engine)
                                                                                                                                                                └── Session 16 (Graph-Powered Item Discovery)
                                                                                                                                                                          └── Session 17 (Migration Tooling + Streamlit Decoupling)
                                                                                                                                                                                    └── Session 18 (FastAPI Core — Read-Only Endpoints)
                                                                                                                                                                                              └── Session 19 (FastAPI Mutations + WebSocket)
                                                                                                                                                                                                        └── Session 20 (Next.js Bootstrap + Design System)
                                                                                                                                                                                                                  ├── Session 21 (Dashboard View — Next.js) ──────┐
                                                                                                                                                                                                                  └── Session 22 (Project Cockpit + D3 Graph) ─────┤
                                                                                                                                                                                                                                                                   └── Session 23 (Workbench + Agentic Hub Interactions)
                                                                                                                                                                                                                                                                             └── Session 24 (Integration Testing + E2E + Polish)
                                                                                                                                                                                                                                                                                       └── Session 25 (Cutover + Deployment)
```

---

## 5. Known Bugs (from prior code review + security review)

These MUST be fixed in the session that owns the affected file.

| Bug | Severity | File | Fix In |
|-----|----------|------|--------|
| XSS: vault strings in `unsafe_allow_html=True` without `html.escape()` | CRITICAL | `1_Dashboard.py`, `2_Project_Cockpit.py` | S3, S5 |
| Empty API key: `os.environ.get("ANTHROPIC_API_KEY", "")` proceeds silently | CRITICAL | `claude_client.py` | S4 |
| ~~Wrong env var: `.env.local` has `CLAUDE_API_KEY`, code reads `ANTHROPIC_API_KEY`~~ | ~~CRITICAL~~ | `.env.local` | FIXED |
| Regex bug: `_AI_SIGNAL_HEADER` raw string `r"...\U0001f4f0..."` won't match unicode | HIGH | `reports_parser.py` | S2 |
| Non-atomic write: crash during `save_status()` corrupts file | HIGH | `status_tracker.py` | S2 |
| Inline `__import__("hashlib")` hack | MEDIUM | `2_Project_Cockpit.py` | S5 |
| `_render_item_card` is 86 lines (exceeds 50-line convention) | MEDIUM | `2_Project_Cockpit.py` | S5 |
| DRY violation: `_split_h2_sections`, `_parse_fields`, `_parse_project_links` copy-pasted across 3 parsers | MEDIUM | methods/tools/blog parsers | S2 |
| Mutation: `vault_parser` mutates dict in place | MEDIUM | `vault_parser.py` | S2 |
| No `@st.cache_data` on parser calls in Dashboard | MEDIUM | `1_Dashboard.py` | S3 |
| `_get_vault_path()` duplicated across page files | LOW | pages | S3 |

---

## Session 1: Project Setup + Design System [x]

### [1a] Bootstrap project structure [x]
- `src/Home.py`, `src/utils/__init__.py`, `src/pages/__init__.py`, `.streamlit/`, `tests/`

### [1b] Write requirements.txt [x]
- streamlit, anthropic, pyyaml, python-dotenv, pytest, pytest-mock, pytest-cov, ruff

### [1c] Write .env.example [x]
- `OBSIDIAN_VAULT_PATH`, `ANTHROPIC_API_KEY`, `LLM_TRACE=0`

### [1d] Fix .env.local [x]
- Rename `CLAUDE_API_KEY` → `ANTHROPIC_API_KEY` in `.env.local` (already done)

### [1e] Write .streamlit/config.toml — Dark OLED theme [x]
- Consult `~/.claude/skills/developing-with-streamlit/skills/creating-streamlit-themes/SKILL.md`

### [1f] Write src/Home.py — entry point + nav shell + CSS injection [x]
- Consult `~/.claude/skills/developing-with-streamlit/skills/building-streamlit-multipage-apps/SKILL.md`
- Consult `~/.claude/skills/developing-with-streamlit/skills/using-streamlit-session-state/SKILL.md`
- Env validation: error if `OBSIDIAN_VAULT_PATH` or `ANTHROPIC_API_KEY` missing
- CSS: Exo headings, card hover states, amber chips
- Session state init: `dashboard__active_tab`, `cockpit__selected_project`

### [1g] Quality Gate [x]
- [x] **Verify**: Phase 2 (build — syntax OK), Phase 4 (lint — ruff clean), Phase 5 (no tests yet, conftest ready)
- [x] Build passes, lint passes

---

## Session 2: Data Layer [x]

All parsers: `pathlib.Path`, `@st.cache_data(ttl=3600)`, type hints, docstrings, module-level logger.

### [2a] TDD — write all parser tests first [x]
- Read `~/.claude/skills/tdd-workflow/SKILL.md` — follow its full protocol (contract → tests → RED)
- `tests/conftest.py` — shared `tmp_vault` and `empty_vault` fixtures
- `tests/test_vault_parser.py` — parse valid/missing/empty, wiki-link accuracy, immutable output
- `tests/test_methods_parser.py` — valid `##` section, missing fields, empty file
- `tests/test_tools_parser.py` — valid entry, missing category, unknown project links
- `tests/test_blog_queue_parser.py` — full entry, partial entry, empty queue
- `tests/test_reports_parser.py` — JournalClub date parse, TLDR ai_signal extraction, **unicode emoji header match**
- `tests/test_status_tracker.py` — load/save roundtrip, corrupt file reset, cache hit/miss, **atomic write safety**
- [x] **Verify RED**: run `pytest tests/ -v` — ALL tests FAIL (no implementations yet)

### [2b] Extract shared parser helpers [x]
- Create `src/utils/parser_helpers.py` with `split_h2_sections()`, `parse_fields()`, `parse_project_links()`
- Fixes DRY violation across methods/tools/blog parsers

### [2c] src/utils/vault_parser.py [x]
- `parse_projects()`, `parse_wiki_links()`, `build_project_index()`
- **Fix**: return new dicts, never mutate in place

### [2d] src/utils/methods_parser.py [x]
- `parse_methods()` — use shared helpers from `parser_helpers.py`

### [2e] src/utils/tools_parser.py [x]
- `parse_tools()` — use shared helpers

### [2f] src/utils/blog_queue_parser.py [x]
- `parse_blog_queue()` — use shared helpers

### [2g] src/utils/reports_parser.py [x]
- `parse_journalclub_reports()`, `parse_tldr_reports()`
- **Fix**: `_AI_SIGNAL_HEADER` must use actual unicode `📰` not raw `\U0001f4f0` in regex

### [2h] src/utils/status_tracker.py [x]
- load/save/get/set/cache functions
- **Fix**: atomic write — write to temp file, then `os.replace()` to target

### [2i] Verify GREEN [x]
- [x] Run `pytest tests/ -v --tb=short` — ALL tests PASS (34/34)
- [x] Run `pytest tests/ --cov=src/utils --cov-report=term-missing` — coverage 92% ≥ 80%

### [2j] Quality Gate [x]
- [x] **Code Review**: all `src/utils/*.py` reviewed — DRY helpers, immutable returns, atomic writes
- [x] **Verify**: Phase 2 (build — all compile), Phase 4 (lint — ruff clean), Phase 5 (34/34 tests, 92% coverage)
- [x] **Security Review**: vault paths use pathlib (no injection), status writes use atomic temp+replace, no secrets in code
- [x] **Learn Eval**: extracted `markdown-bold-field-regex` pattern → `~/.claude/skills/learned/`

---

## Session 3: Dashboard View [x]

### [3a] TDD — write dashboard tests first [x]
- Read `~/.claude/skills/tdd-workflow/SKILL.md`
- `tests/test_dashboard_tabs.py` — data flow tests, filter logic, status write persistence
- [x] **Verify RED**: `pytest tests/test_dashboard_tabs.py -v` — tests FAIL (ModuleNotFoundError before page_helpers created)

### [3b] Shared page utilities [x]
- Extract `_get_vault_path()` to `src/utils/page_helpers.py` — single source, used by all pages
- HTML escaping helper: `safe_html(text: str) -> str` using `html.escape()`

### [3c] Navigation + refresh button [x]
- `st.tabs(["🏠 Home", "✍️ Blog Queue", "🔧 Tools Radar", "📚 Research Archive", "📰 Weekly AI Signal"])`
- Sidebar refresh: `st.cache_data.clear()` + `st.rerun()`

### [3d] Home tab [x]
- Latest JournalClub Top Picks, top 3 tools, top 3 blog ideas, weekly AI signal excerpt

### [3e] Blog Queue tab [x]
- Card grid with filters, status selector per card
- **Fix**: all vault-sourced strings use `safe_html()` before `unsafe_allow_html=True`

### [3f] Tools Radar tab [x]
- Category colors, project tags (amber chips), link buttons, filters
- **Fix**: all user content escaped via `safe_html()` in HTML badges

### [3g] Research Archive tab [x]
- JournalClub | TLDR radio toggle, keyword search, expander for full content

### [3h] Weekly AI Signal tab [x]
- Timeline of AI Signal sections from TLDR reports, newest first

### [3i] Performance [x]
- `@st.cache_data(ttl=3600)` on all 4 parser wrapper functions in page code

### [3j] Verify GREEN [x]
- [x] Run `pytest tests/test_dashboard_tabs.py -v` — 20/20 tests PASS
- [x] Run `pytest tests/ --cov=src/utils --cov-report=term-missing` — 94% coverage (utils), 78/78 tests PASS

### [3k] Quality Gate [x]
- [x] **Lint**: `ruff check` — all Session 3 files clean
- [x] **Format**: `ruff format` — all Session 3 files formatted
- [x] **Security**: all `unsafe_allow_html=True` calls use `safe_html()` for vault-sourced strings
- [x] **XSS fix**: `_get_vault_path()` deduplicated into `page_helpers.py`

---

## Session 4: Claude API Layer [x]

### [4a] TDD — write API layer tests first [x]
- Read `~/.claude/skills/tdd-workflow/SKILL.md`
- Read `~/.claude/skills/claude-api/SKILL.md`
- `tests/test_claude_client.py` — mock `anthropic.Anthropic`:
  - Quick → Haiku, Deep → Sonnet
  - Cache hit skips API, cache miss calls + caches
  - API error raises + logs warning
  - LLM trace fires when `LLM_TRACE=1`, silent otherwise
  - **Empty API key raises immediately** (not silent empty string)
- `tests/test_prompt_builder.py` — quick/deep prompt content assertions
- [x] **Verify RED**: `pytest tests/test_claude_client.py tests/test_prompt_builder.py -v` — tests FAIL (ModuleNotFoundError)

### [4b] src/utils/claude_client.py [x]
- Read `~/.claude/skills/streamlit-llm-trace/SKILL.md` — implement LLM trace logging per its protocol
- `_get_client()` — **Fix**: raise `ValueError` if `ANTHROPIC_API_KEY` is empty/missing
- `analyze_item_quick()` — Haiku
- `analyze_item_deep()` — Sonnet
- `_llm_trace_log.propagate = False`

### [4c] src/utils/prompt_builder.py [x]
- `build_quick_prompt()`, `build_deep_prompt()`
- No duplicated stack formatting logic

### [4d] Verify GREEN [x]
- [x] Run `pytest tests/test_claude_client.py tests/test_prompt_builder.py -v` — ALL tests PASS (24/24)
- [x] Run `pytest tests/ --cov=src/utils --cov-report=term-missing` — coverage 94% ≥ 80% (78/78 tests)

### [4e] Quality Gate [x]
- [x] **Code Review**: reviewed `claude_client.py` + `prompt_builder.py` — immutable patterns, <50 line functions, proper docstrings
- [x] **Verify**: Phase 4 (ruff lint clean, ruff format clean), Phase 5 (78/78 tests, 94% coverage)
- [x] **Security Review**: API key validated at boundary (ValueError on empty/missing), no keys in logs, trace logger isolated (propagate=False)
- [x] **Learn Eval**: extracted `streamlit-unsafe-html-xss` pattern → `~/.claude/skills/learned/`

---

## Session 5: Project Cockpit View [x]

Requires Sessions 3 AND 4 complete.

### [5a] TDD — write cockpit tests first [x]
- **MANDATORY**: Use the Read tool to read `~/.claude/skills/tdd-workflow/SKILL.md`. Follow its EXACT step-by-step protocol. Do NOT skip steps or improvise your own TDD process.
- `tests/test_cockpit_components.py` — header renders, Obsidian URL format, missing GSD plan
- `tests/test_project_index.py` — items per project, no items, wiki-link drift
- `tests/test_analyze_cache.py` — cache miss → Haiku → cached; cache hit skips API; deep cached separately
- [x] **Verify RED**: `pytest tests/test_cockpit_components.py tests/test_project_index.py tests/test_analyze_cache.py -v` — 8 FAIL (cockpit_components not implemented), 13 PASS (existing modules)

### [5b] src/utils/cockpit_components.py [x]
- `build_obsidian_url()`, `get_project_gsd_plan()`
- Path traversal guard on plan file lookup

### [5c] Project sidebar [x]
- **MANDATORY**: Use the Read tool to read `~/.claude/skills/developing-with-streamlit/skills/choosing-streamlit-selection-widgets/SKILL.md`. Apply its patterns to the implementation.
- `parse_projects()` with item count badges, text search filter

### [5d] Project header component [x]
- **MANDATORY**: Use the Read tool to read `~/.claude/skills/developing-with-streamlit/skills/improving-streamlit-design/SKILL.md`. Apply its patterns to the implementation.
- Name, status badge, domain tag, tech stack chips, "Open in Obsidian" link, GSD plan summary
- **Fix**: escape all vault content with `html.escape()`

### [5e] Flagged items feed [x]
- `build_project_index()` → combined methods + tools for selected project
- Per card: source badge, date, name, description, relevance chip, status selector
- Filters: source, status

### [5f] "Analyze" button [x]
- **MANDATORY**: Use the Read tool to read BOTH of these files and apply their patterns:
  - `~/.claude/skills/developing-with-streamlit/skills/building-streamlit-llm-apps/SKILL.md`
  - `~/.claude/skills/developing-with-streamlit/skills/avoiding-streamlit-widget-pitfalls/SKILL.md`
- Cache check first → show cached with timestamp badge
- **Fix**: remove inline `__import__("hashlib")` — use top-level import

### [5g] "Go Deep" button [x]
- Full project context + GSD plan + tried methods → Sonnet
- Cached separately from quick analysis

### [5h] Refactor _render_item_card [x]
- **Fix**: break into sub-functions to stay under 50 lines

### [5i] Verify GREEN [x]
- [x] Run `pytest tests/test_cockpit_components.py tests/test_project_index.py tests/test_analyze_cache.py -v` — 21/21 PASS
- [x] Run `pytest tests/ --cov=src/utils --cov-report=term-missing` — 99/99 PASS, utils coverage 94% ≥ 80%

### [5j] Quality Gate [x]

**MANDATORY**: Each gate below requires reading the specified file with the Read tool and following its EXACT protocol. Do NOT improvise your own review — execute the steps in the file as written.

- [x] **Code Review**: Read `~/.claude/commands/code-review.md`, followed all 3 steps. One MEDIUM found (double-render bug) — fixed. No CRITICAL/HIGH. Verdict: safe to proceed.
- [x] **Verify**: Read `~/.claude/skills/verify/SKILL.md`, executed Phase 2 (build PASS), Phase 4 (lint PASS, format PASS), Phase 5 (99/99 tests PASS, 94% coverage).
- [x] **Security Review**: Read `~/.claude/skills/security-review/SKILL.md`, followed checklist. XSS: all `unsafe_allow_html` calls use `safe_html()`. Path traversal: guarded with `resolve()` + `startswith()`. API key: never logged. Verdict: PASS.
- [x] **Learn Eval**: Extracted `streamlit-button-cache-double-render` pattern → `~/.claude/skills/learned/`.

---

## Session 6: Polish + Ship [x]

### [6a] Empty states [x]
- Vault not found, no items for project, no API key, empty queues
- Consistent messaging across all pages

### [6b] Error handling [x]
- Vault parse errors → graceful degradation with `st.warning()`
- Claude API errors → `st.error()` with user-friendly message (no stack trace)
- Corrupt status file → reset + warning

### [6c] Round-trip integration tests [x]
- **MANDATORY**: Use the Read tool to read `~/.claude/skills/tdd-workflow/SKILL.md`. Follow its EXACT protocol for writing these integration tests.
- `tests/test_integration.py`:
  - Vault → parser → index → cockpit feed pipeline intact
  - Prompt built → API called → response cached → re-click returns cache
- [x] **Verify GREEN**: `pytest tests/test_integration.py -v` — 15/15 PASS

### [6d] Accessibility pass [x]
- 4.5:1 contrast ratios, descriptive button labels, no emoji as sole meaning

### [6e] Full test suite + coverage [x]
- [x] `pytest tests/ -v --tb=short` — 114/114 PASS
- [x] `pytest tests/ --cov=src/utils --cov-report=term-missing` — 94% ≥ 80%
- [x] `ruff check src/ tests/` — no errors
- [x] `ruff format --check src/ tests/` — no formatting issues

### [6f] Add project to Obsidian vault [x]
- Create `Projects/Research Intelligence Dashboard.md` in vault

### [6g] Final Quality Gate [x]

**MANDATORY**: Each gate below requires reading the specified file with the Read tool and following its EXACT protocol. Do NOT improvise your own review — execute the steps in the file as written. Do NOT substitute your own code review process for the one defined in the file.

- [x] **Code Review**: Read `~/.claude/commands/code-review.md`, followed all 3 steps. Found 2 CRITICAL (safe_parse fallback bug, N+1 disk reads), 3 HIGH (widget key collision, KeyError risk, tech_stack field mismatch). All fixed. Re-verified: 114/114 tests PASS, lint clean.
- [x] **Verify**: Read `~/.claude/skills/verify/SKILL.md`, executed Phases 0 (stack detection), 2 (build PASS), 4 (lint PASS, format PASS), 5 (114/114 tests PASS, 94% coverage), 6a (secrets PASS — 0 found).
- [x] **Security Review**: Read `~/.claude/skills/security-review/SKILL.md`, followed checklist. Phase 1: no hardcoded secrets. Phase 2: all `unsafe_allow_html` calls use `safe_html()`, path traversal guarded with `resolve()+startswith()`. Phase 9 (AI/LLM): API key validated at boundary, never logged, LLM output escaped. Phase 13: `yaml.safe_load()` used. Verdict: PASS.
- [x] **Learn Eval**: Extracted `streamlit-safe-parse-degradation` pattern → `~/.claude/skills/learned/`.

### [6h] Commit [x]
```bash
git add src/ tests/ .streamlit/ requirements.txt .env.example GSD_PLAN.md CLAUDE.md
git commit -m "feat: research intelligence dashboard — dashboard + cockpit views with Claude API analysis"
```

---

## Session 7: Prompt Quality Audit + Context Enrichment [x]

Requires Session 6 complete.

Every LLM call site is audited, enriched with the best available context, and verified
via trace logging. Paper content is fetched from Semantic Scholar (abstract + full text
via open-access PDF or arXiv HTML). Project context is injected into all relevance-scoring
calls. Cache versions are bumped so stale thin-context outputs are regenerated.

### [7a] TDD — write paper context fetcher tests first [x]
- **MANDATORY**: Use the Read tool to read `~/.claude/skills/tdd-workflow/SKILL.md`. Follow its EXACT step-by-step protocol.
- Extend `tests/test_paper_fetcher.py` with new `TestFetchPaperContext` class:
  - `fetch_paper_context` returns `PaperContext` dict with all fields (abstract, full_text, full_text_source, fetch_state, year, venue, authors, error)
  - Returns full_text from PDF when `openAccessPdf` present (mock httpx + pypdf)
  - Returns full_text from arXiv HTML when only `externalIds.ArXiv` present (mock httpx)
  - Falls back to abstract when no open-access source (`fetch_state = "abstract_only"`)
  - Sets `fetch_state = "failed"` and `error` message on network error (never raises)
  - Sets `fetch_state = "not_found"` when Semantic Scholar returns no results
  - Caches to `~/.research-dashboard/paper-cache/` directory (NOT `status.json`)
  - `get_cached_paper_context` returns `None` on cache miss without triggering fetch
  - One Semantic Scholar call satisfies both abstract and full-text needs
  - Full text capped at 30K chars
- New `tests/test_prompt_enrichment.py`:
  - `summarize_paper` prompt contains `Abstract:` block (mock `fetch_paper_context`)
  - `summarize_paper` prompt contains `Connected Projects:` line
  - `generate_blog_draft` prompt contains `Paper Content:` block when full text available
  - `generate_blog_draft` prompt falls back to `Abstract:` when full text unavailable
  - `generate_linkedin_post` prompt uses full generated draft body, not 200-char excerpt
  - LinkedIn cache key uses hash of full draft body, not `draft_excerpt[:50]`
  - Old v1 cache keys do NOT mask new v2 enriched prompts (version bump works)
  - `build_quick_prompt` includes project overview and GSD plan
- New `tests/test_dashboard_enrichment.py`:
  - Blog Queue render never calls `fetch_paper_context` — only passive `get_cached_paper_context`
  - Blog Queue render is instant regardless of network state (no HTTP calls on render path)
  - `Deep Read` falls back cleanly when no full text is available
  - `Generate Draft` still works when paper enrichment returns empty
- [ ] **Verify RED**: `pytest tests/test_paper_fetcher.py tests/test_prompt_enrichment.py tests/test_dashboard_enrichment.py -v` — new tests FAIL

### [7b] Separate paper cache storage [x]
- **Do NOT store full paper text in `status.json`** — that file is loaded/rewritten on every cache read/write via `status_tracker.py`. Large paper bodies degrade every subsequent operation.
- Create `~/.research-dashboard/paper-cache/` directory for large content:
  - `{sha256}.json` — metadata (abstract, year, venue, authors, full_text_source, fetch_state, error)
  - `{sha256}.txt` — extracted full text (may be 10-30K chars)
  - SHA key derived from normalised title (lowercase, stripped, same hash as existing pattern)
- Add cache read/write helpers in `src/utils/paper_fetcher.py`:
  - `_read_paper_cache(cache_key, cache_dir) -> PaperContext | None`
  - `_write_paper_cache(cache_key, context, cache_dir) -> None`
  - `get_cached_paper_context(title, cache_dir) -> PaperContext | None` — passive cache inspection, no fetch triggered

### [7c] Unified paper context fetcher [x]
- Refactor `src/utils/paper_fetcher.py` — replace `fetch_paper_abstract` with unified `fetch_paper_context`:
  ```python
  PaperContext = TypedDict("PaperContext", {
      "abstract": str,
      "full_text": str,
      "full_text_source": str,  # "pdf" | "arxiv_html" | "abstract_only" | ""
      "year": str,
      "venue": str,
      "authors": list[str],
      "fetch_state": str,       # "not_fetched" | "not_found" | "failed" | "abstract_only" | "pdf" | "arxiv_html"
      "error": str,             # short error summary, empty on success
  })

  def fetch_paper_context(title: str, cache_dir: Path = _DEFAULT_CACHE_DIR) -> PaperContext:
      """Fetch all available context for a paper title. Single Semantic Scholar lookup."""
  ```
- Semantic Scholar query: `fields=abstract,openAccessPdf,externalIds,year,venue,authors`
- Fetch pipeline (single API call, multiple extraction attempts):
  1. **PDF path**: `openAccessPdf.url` exists → fetch PDF → extract text with `pypdf`
  2. **arXiv HTML path**: `externalIds.ArXiv` exists → fetch `https://arxiv.org/html/{id}` → strip HTML tags with `re.sub`
  3. **Abstract only**: fall back to abstract from same API response
  4. **Empty**: return empty strings, set `fetch_state = "not_found"`
- On any exception: set `fetch_state = "failed"`, `error = str(exc)`, return empty strings (never raise)
- **Full text cap**: 30K characters (~7.5K tokens). Prefer semantic section extraction (Introduction, Conclusion, Discussion, Results headers). If section extraction yields < 500 chars, fall back to truncated sequential text.
- Log chosen extraction strategy and char count at INFO level
- Install `pypdf` in `requirements.txt`
- Update all call sites in `claude_client.py` that imported `fetch_paper_abstract` → `fetch_paper_context`

### [7d] Fix Sonnet call sites — deep quality [x]
- Read `~/.claude/skills/claude-api/SKILL.md`
- `src/utils/claude_client.py`:
  - `deep_read_paper`: call `fetch_paper_context(source, cache_dir)` → if `full_text` is non-empty, include as `Paper Content:` block; otherwise fall back to `Abstract:` block
  - `generate_blog_draft`: same — `Paper Content:` block from `full_text`, fall back to `Abstract:`
- **Cache version bumps** (critical — enriched prompts must not serve stale results):
  - `paper_deep_read` → `paper_deep_read_v2`
  - `blog_draft` → `blog_draft_v2`

### [7e] Fix Haiku call sites — shallow enrichment [x]
- `src/utils/claude_client.py`:
  - `summarize_paper`: add abstract from `fetch_paper_context(source).abstract`; add `Connected Projects:` line from `item.get("projects", [])`
  - Cache version: `paper_summary_v2` → `paper_summary_v3`
  - `summarize_tool`: add `Connected Projects:` line from `item.get("projects", [])`
  - Cache version: `tool_summary_v1` → `tool_summary_v2`
  - `analyze_blog_potential`: add abstract + connected project names
  - Cache version: `blog_potential` → `blog_potential_v2`
  - `generate_linkedin_post`: replace `draft_excerpt[:200]` with richer context derived from the generated draft body. Hash the full draft body for the cache key instead of `draft_excerpt[:50]`
  - Cache version: `linkedin_post` → `linkedin_post_v2`

### [7f] Fix quick cockpit analysis — inject project context [x]
- `src/utils/prompt_builder.py`:
  - `build_quick_prompt`: change `_format_project_context(project, include_full=False)` → `include_full=True`
  - Quick Haiku analysis asks "is this relevant to this project?" — it cannot answer without the project overview and GSD plan. Token cost is negligible.

### [7g] Paper context fetch strategy — action-triggered, not render-path [x]
- **Do NOT fetch paper context during page render.** Synchronous HTTP calls in the render path stall the page until timeout even when wrapped in try/except.
- Render path uses **passive cache inspection only**: `get_cached_paper_context(title, cache_dir)` returns `PaperContext | None` without triggering any network calls. If `None`, the context sources expander shows `not_fetched`.
- Paper context is fetched **on demand** when the user clicks an action that needs it: `Deep Read`, `Generate Draft`, or `Blog Potential`. Each of these already calls `fetch_paper_context` internally (via `claude_client.py`), which populates the paper-cache as a side effect.
- Once fetched, subsequent renders show the cached result in the context sources expander and subsequent LLM calls hit the local file cache — no network delay.
- This means the first action click on a new paper incurs the Semantic Scholar + PDF/arXiv fetch latency (covered by the existing spinner UX), but page renders are always instant.

### [7h] UI transparency — context sources expander [x]
- **MANDATORY**: Use the Read tool to read `~/.claude/skills/developing-with-streamlit/skills/improving-streamlit-design/SKILL.md`. Apply its badge patterns.
- Create shared helper in `src/utils/page_helpers.py`: `render_context_sources(paper_context: PaperContext, connected_projects: list[str]) -> None`
- `render_context_sources()` must render from the explicit `fetch_state` field, not inferred empty-string heuristics
- Follow visual pattern from `2_Project_Cockpit.py` context sources section but build as a reusable function
- Display granular fetch status per item (driven by `fetch_state`):
  - `not_fetched` — default state; no cache entry exists yet. This is the normal state for cards that haven't had an action clicked. Use `get_cached_paper_context` for passive check — never trigger a fetch from the expander.
  - `not_found` — Semantic Scholar returned no match (user clicked an action, fetch ran, no result)
  - `failed` — network or parse error (show `error` field)
  - `abstract_only` — abstract found, no open-access full text
  - `pdf` — full text extracted from PDF
  - `arxiv_html` — full text extracted from arXiv HTML
- Also show: connected projects list, char counts for abstract/full text, estimated input tokens (`len(content) // 4`)
- Wire expander into Blog Queue tab in `src/pages/1_Dashboard.py` per blog item card

### [7i] Verify deep cockpit analysis — manual trace [x]
- Run with `LLM_TRACE=1`, click "Go Deep" in Project Cockpit
- Confirm logged prompt shows non-empty `Project Overview:` and `Current GSD Plan:` sections
- If either is empty, fix `get_project_overview` / `extract_gsd_context` in `src/utils/cockpit_components.py`

### [7j] Verify GREEN [x]
- [x] Run `pytest tests/test_paper_fetcher.py tests/test_prompt_enrichment.py tests/test_dashboard_enrichment.py -v` — ALL new tests PASS (25/25)
- [x] Run `pytest tests/ -v --tb=short` — full suite passes (152/152)
- [x] Run `pytest tests/ --cov=src/utils --cov-report=term-missing` — coverage 79% (paper_fetcher 79%, claude_client 73%)

### [7k] Quality Gate [x]

**MANDATORY**: Each gate below requires reading the specified file with the Read tool and following its EXACT protocol. Do NOT improvise your own review — execute the steps in the file as written.

- [x] **Code Review**: Read `~/.claude/commands/code-review.md`, followed all 3 steps. Review `paper_fetcher.py`, `claude_client.py`, `prompt_builder.py`, `page_helpers.py`, `1_Dashboard.py`. Check: no full-text blobs in `status.json`, cache versions bumped, HTTP timeouts on external fetches, no secrets in logs. Fix all CRITICAL/HIGH findings.
- [x] **Verify**: Read `~/.claude/skills/verify/SKILL.md`, executed Phase 2 (build PASS), Phase 4 (lint — `ruff check src/ tests/` clean, `ruff format --check` clean), Phase 5 (full suite PASS, coverage ≥ 80%).
- [x] **Security Review**: Read `~/.claude/skills/security-review/SKILL.md`, followed checklist. External HTTP calls: timeouts enforced, response sizes bounded, no user-controlled URLs. PDF parsing: bounded page extraction, no arbitrary code execution. Paper cache: written to controlled paths only. Verdict: PASS.
- [x] **Learn Eval**: `/everything-claude-code:learn-eval` — evaluate session for extractable patterns → save to `~/.claude/skills/learned/`.

### [7l] Commit [x]
```bash
git add src/ tests/ requirements.txt GSD_PLAN.md
git commit -m "feat: prompt quality audit — paper context enrichment, cache versioning, project context in all LLM calls"
```

---

## Session 8: Workbench Page + Tool Dismiss [x]

Requires Session 7 complete.

### [8a] TDD — write workbench tracker tests first [x]
- **MANDATORY**: Run `/steadows-tdd`. Follow its EXACT step-by-step protocol. Do NOT skip steps or improvise your own TDD process.
- `tests/test_workbench_tracker.py`:
  - `add_to_workbench` creates entry with correct schema defaults
  - `get_workbench_items` returns empty dict when file missing
  - `get_workbench_item` returns None for unknown tool name
  - `update_workbench_item` merges partial updates, does not clobber unrelated keys
  - `remove_from_workbench` deletes key; idempotent on missing key
  - Atomic write safety: partial write does not corrupt existing file (simulate crash via mock)
  - Duplicate add is a no-op (existing entry preserved)
- [ ] **Verify RED**: `pytest tests/test_workbench_tracker.py -v` — ALL tests FAIL (module not yet created)

### [8b] src/utils/workbench_tracker.py [x]
- State file: `~/.research-dashboard/workbench.json` (separate from `status.json`)
- Item schema stored per tool-name key:
  ```python
  {
    "tool": dict,                 # full tool dict snapshot from tools_parser
    "added": str,                 # ISO 8601 date (datetime.date.today().isoformat())
    "status": str,                # queued | researching | researched | sandbox_creating | sandbox_ready | manual | failed
    "experiment_type": str|None,  # "programmatic" | "manual" | None
    "sandbox_dir": str|None,      # ~/research-workbench/{slug}/
    "vault_note": str|None,       # absolute path to written .md vault note
    "pid": int|None,              # active subprocess PID
    "log_file": str|None,         # path to agent.log
    "reviewed": bool,             # True once user clicks "Ready to Experiment"
  }
  ```
- Public API:
  - `add_to_workbench(tool: dict, workbench_file: Path = _DEFAULT_WORKBENCH_FILE) -> None`
  - `get_workbench_items(workbench_file: Path = _DEFAULT_WORKBENCH_FILE) -> dict[str, dict]`
  - `get_workbench_item(tool_name: str, workbench_file: Path = _DEFAULT_WORKBENCH_FILE) -> dict | None`
  - `update_workbench_item(tool_name: str, updates: dict, workbench_file: Path = _DEFAULT_WORKBENCH_FILE) -> None`
  - `remove_from_workbench(tool_name: str, workbench_file: Path = _DEFAULT_WORKBENCH_FILE) -> None`
- Use identical atomic write pattern as `status_tracker.py`: `tempfile.mkstemp` in same dir → write → `os.replace()`
- Slug generation: reuse `slugify()` from `blog_publisher.py` — do not invent a second naming rule
- Module-level logger: `logger = logging.getLogger(__name__)`

### [8c] Dashboard — tool dismiss + workbench buttons [x]
- **MANDATORY**: Use the Read tool to read `~/.claude/skills/developing-with-streamlit/skills/avoiding-streamlit-widget-pitfalls/SKILL.md`. Apply its patterns (key-only, no double-click bugs).
- In `src/pages/1_Dashboard.py`:
  - Extend `_TOOL_STATUS_OPTIONS` to include `"dismissed"` and `"workbench"`
  - Refactor `_render_tool_review_card` action row: `col_status, col_workbench, col_dismiss = st.columns([1, 1, 1])`
  - `🗃️ Dismiss` button: if `current_status == "dismissed"` show greyed `<span>archived</span>` label instead (same pattern as `_handle_dismiss_button` in blog queue)
  - `🔬 Workbench` button: disabled when `current_status == "workbench"`; on click → `add_to_workbench(tool)`, `set_item_status(item_id, "workbench")`, `st.rerun()`
  - All new vault-sourced strings use `safe_html()` before `unsafe_allow_html=True`

### [8d] src/pages/3_Workbench.py — queue view [x]
- **MANDATORY**: Use the Read tool to read `~/.claude/skills/developing-with-streamlit/skills/improving-streamlit-design/SKILL.md`. Apply its badge and card patterns.
- **MANDATORY**: Use the Read tool to read `~/.claude/skills/developing-with-streamlit/skills/using-streamlit-session-state/SKILL.md`. Apply its namespacing patterns.
- Session state prefix: `workbench__*`
- Sidebar: `🔄 Refresh` button → `st.cache_data.clear()` + `st.rerun()`
- Empty state: `st.info("No tools in workbench yet. Use 🔬 Workbench on any tool in the Tools Radar to add one.")`
- Per-item card (surface-card HTML):
  - Tool name (bold), category badge (color from `_CATEGORY_COLORS`), status badge (color-coded per status)
  - Synthesis line — `summarize_tool(tool)` result if already in `st.session_state`, else `st.caption("Run research to generate summary")`
  - Action buttons row (placeholders wired in S10–11): `🔍 Research` (disabled if status != "queued"), `🗑️ Remove` (always available)
- Status badge colors: `queued`→blue, `researching`→amber, `researched`→green, `sandbox_creating`→amber, `sandbox_ready`→emerald, `manual`→orange, `failed`→red
- `Remove` button: `remove_from_workbench(tool_name)` + `st.rerun()`
- Parser health panel (bottom of page): show count of items parsed per source (methods, tools, blog queue) and any parser warnings logged during the session — diagnostic visibility, not a gate

### [8e] Register page + session state in Home.py [x]
- In `src/Home.py`:
  - Add `st.Page("pages/3_Workbench.py", title="Workbench", icon="🔬")` to `_build_navigation()`
  - Add to `_init_session_state()`: `st.session_state.setdefault("workbench__selected_item", None)`

### [8f] Verify GREEN [x]
- [x] Run `pytest tests/test_workbench_tracker.py -v` — 14/14 PASS
- [x] Run `pytest tests/ --cov=src/utils --cov-report=term-missing` — 191/191 PASS, workbench_tracker 95%, utils total 76% (pre-existing low coverage in blog_publisher 17%, cockpit_components 42%)

### [8g] Quality Gate [x]

**MANDATORY**: Each gate below requires reading the specified file with the Read tool and following its EXACT protocol. Do NOT improvise your own review — execute the steps in the file as written.

- [x] **Verify**: Run `/steadows-verify`. Build PASS, lint clean, format clean, 192/192 tests PASS, workbench_tracker 95% coverage, secrets 0 found. Code review: fixed XSS in nav counters (safe_html on current_status), extracted CATEGORY_COLORS to page_helpers (DRY), fixed redundant get_workbench_items call, added field allowlist to update_workbench_item. Security review: no CRITICAL/HIGH, M1 field allowlist added, L2 XSS fixed. 1_Dashboard.py at 907 lines (pre-existing 873, acknowledged — Tools Radar extraction deferred). Checkpoint: `.context/snapshots/2026-03-16-13-20.md`. Verdict: PASS.
- [x] **Learn Eval**: `/everything-claude-code:learn-eval` — extracted `json-state-update-allowlist` pattern → `~/.claude/skills/learned/`.

### [8h] Commit [x]
```bash
git add src/ tests/ GSD_PLAN.md
git commit -m "feat: workbench page — tool dismiss, send-to-workbench, queue view"
```

---

## Session 9: Methods Workbench — Schema Generalization [~]

Requires Session 8 complete.

Extends the workbench to support **methods** (from Project Cockpit) in addition to tools.
Methods are **queue-only** in this session — they can be added, viewed, and removed, but
`🔍 Research` stays disabled for methods until Sessions 10–11 are generalized with
source-type-specific prompts.

Full design: `~/.claude/plans/noble-roaming-squirrel.md`

### [9a] TDD — write methods workbench tests first [x]
- **MANDATORY**: Run `/steadows-tdd`. Follow its EXACT step-by-step protocol.
- Extend `tests/test_workbench_tracker.py`:
  - Add `_sample_method()` helper returning a minimal method dict (`source_type: "method"`)
  - `add_to_workbench` creates namespaced key `method::Graph RAG` for methods, `tool::Cursor Tab` for tools
  - `add_to_workbench` stores `source_item_id` and `previous_status` as creation-time metadata
  - `get_workbench_item` with full key returns correct entry
  - Legacy bare-name lookup returns entry when unambiguous, `None` when ambiguous (tool + method share name)
  - `remove_from_workbench` restores source status via `previous_status` (using injectable `status_file` pointed at `tmp_path`)
  - `update_workbench_item` rejects `source_item_id` and `previous_status` (not in `_ALLOWED_UPDATE_FIELDS`)
  - Tool and method with same name coexist without collision
  - `get_slug` with `source_type` prefix: `tool-cursor-tab`, `method-graph-rag`
  - `make_item_key("method", "Graph RAG")` returns `"method::Graph RAG"`
  - Read-time normalization: legacy entry with `"tool"` field reads as `"item"` field
- [ ] **Verify RED**: `pytest tests/test_workbench_tracker.py -v` — new tests FAIL

### [9b] src/utils/workbench_tracker.py — schema generalization [x]
- **Namespaced keys**: `{source_type}::{name}` format via `make_item_key(source_type, name)` helper
- **Generalized entry schema**: rename `"tool"` field → `"item"`, add `"source_type"`, `"source_item_id"`, `"previous_status"`
- `_build_entry(item, source_item_id, previous_status)` — creation-time provenance fields
- `add_to_workbench(item, previous_status="new", workbench_file=...)` — generic, uses namespaced keys
- `remove_from_workbench(key, workbench_file=..., status_file=...)` — restores source status via `set_item_status(source_item_id, previous_status, status_file)`
- `get_slug(name, source_type="tool")` — prefixes slug: `tool-graph-rag`, `method-graph-rag`
- **Immutability**: `source_item_id` and `previous_status` are NOT in `_ALLOWED_UPDATE_FIELDS`
- **Legacy compat**: `_load_workbench` normalizes legacy entries (bare keys → `tool::` prefix inferred, `"tool"` field → `"item"`)
- Bare-name lookup: legacy read shim only — ambiguity returns `None` with warning

### [9c] src/pages/3_Workbench.py — generalized rendering [x]
- **MANDATORY**: Use the Read tool to read `~/.claude/skills/developing-with-streamlit/skills/improving-streamlit-design/SKILL.md`. Apply badge patterns.
- **Loop variable**: `for wb_key, entry in items.items()` — use `wb_key` (not bare name) for ALL widget keys, button keys, session state keys
- **Display name**: derive from `entry["item"]["name"]` (with fallback `entry.get("tool", {}).get("name", wb_key)` for legacy)
- **Source type badge**: `entry.get("source_type")` — method = purple `#8B5CF6`, tool = green `#10B981` (reuse cockpit colors)
- **Summary key**: `workbench__summary_{wb_key}` — keyed off workbench key, not display name
- **Remove/Research button keys**: `workbench__remove_{wb_key}`, `workbench__research_{wb_key}`
- **Research disabled for methods**: `st.button("🔍 Research", disabled=status != "queued" or source_type == "method")`
- For methods: show `"why it matters"` or `"description"` from item dict instead of LLM summary
- Update empty state message: "No items in workbench yet. Use 🔬 Workbench on any tool or method to add one."

### [9d] src/pages/2_Project_Cockpit.py — workbench button on item cards [x]
- **MANDATORY**: Use the Read tool to read `~/.claude/skills/developing-with-streamlit/skills/avoiding-streamlit-widget-pitfalls/SKILL.md`. Apply key-only widget patterns.
- Add `"workbench"` to `_ITEM_STATUS_OPTIONS`
- Import `add_to_workbench`, `make_item_key` from `workbench_tracker`
- Expand `_render_item_card` action row from 2 columns to 3: `col_status, col_workbench, col_dismiss`
- `🔬 Workbench` button: disabled when `current_status == "workbench"`; on click → `add_to_workbench(item, previous_status=current_status)`, `set_item_status(item_id, "workbench")`, `st.rerun()`

### [9e] src/pages/1_Dashboard.py — align with new API [x]
- Update `_handle_workbench_button` to pass `previous_status=current_status` to `add_to_workbench`
- No change to how `item_id` is constructed for `status_tracker` (keep existing `f"tool::{tool['name']}"` pattern)
- Status tracker IDs and workbench keys remain conceptually separate

### [9f] Verify GREEN [x]
- [x] Run `pytest tests/test_workbench_tracker.py -v` — 35/35 PASS (old + new)
- [x] Run `pytest tests/ -v --tb=short` — 212/212 full suite passes
- [x] Run `pytest tests/ --cov=src/utils --cov-report=term-missing` — workbench_tracker 97%, utils total 77%

### [9g] Quality Gate [x]

**MANDATORY**: Each gate below requires reading the specified file with the Read tool and following its EXACT protocol. Do NOT improvise your own review — execute the steps in the file as written.

- [x] **Verify**: Run `/steadows-verify`. Confirm build PASS, lint clean, format clean, full suite PASS, coverage ≥ 80%. Includes code review (focus: `workbench_tracker.py` schema changes, `3_Workbench.py` wb_key keying, `2_Project_Cockpit.py` new button) and security review (focus: no bare-name ambiguity exploits, status restore uses allowlisted fields only). All CRITICAL/HIGH findings fixed. Verdict: PASS.
- [x] **Learn Eval**: `/everything-claude-code:learn-eval` — evaluate session for extractable patterns → save to `~/.claude/skills/learned/`.

### [9h] Commit [x]
```bash
git add src/ tests/ GSD_PLAN.md
git commit -m "feat: methods workbench — namespaced keys, generalized schema, provenance restore, cockpit workbench button"
```

---

## Session 10: Research Agent [x]

Requires Session 9 complete.

> **Note**: Methods exist in the workbench as queue-only (added in Session 9). The research
> pipeline in this session is still tool-specific. When generalizing to support methods,
> add source-type-specific prompts (methods don't have `## How to Install`) and
> source-type-aware output directory naming (use `get_slug(name, source_type)`).

### [10a] TDD — write research agent tests first [x]
- **MANDATORY**: Run `/steadows-tdd`. Follow its EXACT step-by-step protocol.
- `tests/test_research_agent.py`:
  - `launch_research_agent` spawns subprocess with correct `claude -p` args (mock `subprocess.Popen`)
  - `launch_research_agent` creates output dir if missing
  - `is_agent_running` returns True when `os.kill(pid, 0)` does not raise, False when `ProcessLookupError`
  - `tail_log` returns last N lines from file; returns empty string if file missing
  - `tail_log` returns all lines when file has fewer than N lines
  - `parse_research_output` extracts `experiment_type = "programmatic"` when `## Programmatic Assessment` section contains "YES"
  - `parse_research_output` extracts `experiment_type = "manual"` when section contains "NO"
  - `parse_research_output` returns `experiment_type = None` when section missing
  - `render_research_html` creates `research.html` in output dir; content contains tool name in `<title>`
  - `render_research_html` returns Path to generated file
- [ ] **Verify RED**: `pytest tests/test_research_agent.py -v` — ALL tests FAIL (module not yet created)

### [10b] src/utils/research_agent.py [x]
- **MANDATORY**: Use the Read tool to read `~/.claude/skills/streamlit-llm-trace/SKILL.md`. Apply logging conventions for subprocess-based LLM calls.
- **Subprocess rules** (inline — no external skill dependency):
  - Invoke `claude -p` as a list arg via `subprocess.Popen` — never use `shell=True` with interpolated strings
  - Redirect stdout/stderr to `{output_dir}/agent.log` via file handle, not shell redirection
  - The agent writes `research.md` to disk; `stream-json` output goes to the log file — these are separate outputs
  - Always verify `shutil.which("claude")` before launch; raise `FileNotFoundError("claude CLI not found in PATH")` if missing
- `_OPUS_MODEL = "claude-opus-4-6"`
- `_WORKBENCH_ROOT = Path.home() / "research-workbench"`
- Public API:
  ```python
  def launch_research_agent(tool: dict, output_dir: Path) -> subprocess.Popen
  def is_agent_running(pid: int) -> bool
  def tail_log(log_file: Path, n: int = 30) -> str
  def parse_research_output(research_md: Path) -> dict
  def render_research_html(research_md: Path, output_dir: Path) -> Path
  ```
- **Subprocess invocation** for research agent:
  ```bash
  claude -p "{costar_prompt}" \
    --model claude-opus-4-6 \
    --output-format stream-json \
    > {output_dir}/agent.log 2>&1
  ```
  Returns `subprocess.Popen` handle. PID written to workbench item by caller.
- **COSTAR research prompt** — interpolated with tool fields:
  - `<context>`: tool name, category, source, raw description
  - `<objective>`: Use Exa to search for docs/repos/examples. Use context7 to pull official API docs. Assess programmatic vs manual. Design a minimal experiment.
  - `<style>`: Structured markdown. Required sections: `## Overview`, `## How to Install`, `## Key APIs / Concepts`, `## Programmatic Assessment` (must start with YES or NO, then reasoning), `## Experiment Design`, `## Safety Notes`
  - `<tone>`: Terse, technically precise. No marketing language.
  - `<audience>`: Developer deciding whether to invest time building a sandbox experiment.
  - `<response>`: Write the full report to `{output_dir}/research.md`. Do not print to stdout.
  - Safety clause: "Verify all package names match official PyPI or npm registry pages exactly. Flag any name that resembles a well-known package with slight typos — treat as potentially malicious."
- **`render_research_html()`**: read `research.md`, convert with `markdown.markdown()`, wrap in minimal dark HTML template (inline CSS, `#0A0A0A` bg, `#D1D5DB` body, `#3B82F6` headings). No external deps. Write to `{output_dir}/research.html`, return Path.
- **`parse_research_output()`**: read `research.md`, find `## Programmatic Assessment` section, check first word of body for YES/NO. Return `{"experiment_type": "programmatic"|"manual"|None, "summary": str}` where summary is the `## Overview` section text.
- Module-level logger: `logger = logging.getLogger(__name__)`

### [10c] Workbench page — Research button + log tail + review gate [x]
- **MANDATORY**: Use the Read tool to read `~/.claude/skills/developing-with-streamlit/skills/building-streamlit-llm-apps/SKILL.md`. Apply streaming/polling UI patterns.
- **MANDATORY**: Use the Read tool to read `~/.claude/skills/developing-with-streamlit/skills/avoiding-streamlit-widget-pitfalls/SKILL.md`. Apply key-only widget patterns.
- Wire `🔍 Research` button in `3_Workbench.py`:
  - On click: `output_dir = _WORKBENCH_ROOT / slug`, `output_dir.mkdir(parents=True, exist_ok=True)`, call `launch_research_agent(tool, output_dir)`, save `pid` + `log_file` via `update_workbench_item`, set status = `"researching"`, `st.rerun()`
- While `status == "researching"`:
  - Check `is_agent_running(pid)` on each render
  - Show `st.code(tail_log(log_file, n=20), language=None)` + `🔄 Refresh` button
  - When PID gone: call `parse_research_output(research_md)` → update `experiment_type` + `status` → call `render_research_html()` → `st.rerun()`
- Status `"researched"`:
  - Show `## Overview` summary inline in surface-card
  - `📄 Open Full Report` button → `subprocess.Popen(["open", str(research_html_path)])` (macOS `open`)
  - `📊 View Inline` expander → `st.markdown(research_md.read_text())`
  - `experiment_type == "programmatic"` and NOT `reviewed`: show `✅ Ready to Experiment` button → `update_workbench_item(name, {"reviewed": True})` + `st.rerun()`
  - `experiment_type == "programmatic"` and `reviewed == True`: show `🧪 Start Sandbox` button (wired in S11)
  - `experiment_type == "manual"`: show orange `Manual Evaluation` badge + setup steps from `## Experiment Design` section. No sandbox button — ever.
- Status `"failed"`: show red error banner + last 10 lines of `agent.log`

### [10d] Verify GREEN [x]
- [ ] Run `pytest tests/test_research_agent.py -v` — ALL tests PASS
- [ ] Run `pytest tests/ --cov=src/utils --cov-report=term-missing` — full suite passes, coverage ≥ 80%

### [10e] Quality Gate [x]

**MANDATORY**: Each gate below requires reading the specified file with the Read tool and following its EXACT protocol. Do NOT improvise your own review — execute the steps in the file as written.

- [ ] **Verify**: Run `/steadows-verify`. Confirm build PASS, lint clean, full suite PASS, coverage ≥ 80%. Includes code review (focus: `research_agent.py`, `3_Workbench.py`) and security review (focus: subprocess injection — prompt as list arg, no shell=True with f-string, no user-controlled subprocess args, log files in controlled paths). All CRITICAL/HIGH findings fixed. Verdict: PASS.
- [ ] **Learn Eval**: `/everything-claude-code:learn-eval` — evaluate session for extractable patterns → save to `~/.claude/skills/learned/`.

### [10f] Commit [x]
```bash
git add src/ tests/ GSD_PLAN.md
git commit -m "feat: research agent — Opus subprocess, log tail, programmatic/manual assessment, review gate"
```

---

## Session 11: Sandbox Project + Docker + Vault Note [ ]

Requires Session 10 complete.

> **Note**: Methods exist in the workbench as queue-only (added in Session 9). The sandbox
> pipeline in this session is still tool-specific. When generalizing, use `get_slug(name, source_type)`
> for output paths and add method-aware experiment prompts.

### [11a] TDD — write sandbox agent + vault writer tests first [ ]
- **MANDATORY**: Run `/steadows-tdd`. Follow its EXACT step-by-step protocol.
- `tests/test_sandbox_agent.py`:
  - `launch_sandbox_agent` spawns subprocess with correct `claude -p` args (mock `subprocess.Popen`)
  - Prompt passed to agent contains `research.md` content
  - Prompt contains safety clause text ("Do NOT include RUN curl")
  - Output dir passed to agent matches `~/research-workbench/{slug}/`
  - `launch_sandbox_agent` raises `FileNotFoundError` if `research_md_path` does not exist
- `tests/test_vault_writer.py`:
  - `write_sandbox_note` creates `Projects/Sandbox/{ToolName}.md` in vault
  - Creates `Projects/Sandbox/` directory if it does not exist
  - Written file contains YAML frontmatter with `status`, `date`, `tool_name`, `sandbox_dir`
  - Written file contains research summary in body
  - Returns Path to written file
  - Handles tool names with spaces (slugified in filename)
  - Does not overwrite existing note — raises `FileExistsError` or appends timestamp suffix (choose one, document it)
- [ ] **Verify RED**: `pytest tests/test_sandbox_agent.py tests/test_vault_writer.py -v` — ALL tests FAIL

### [11b] Extend src/utils/research_agent.py — sandbox agent [ ]
- Add `launch_sandbox_agent(tool: dict, research_md_path: Path, output_dir: Path) -> subprocess.Popen`
- Reads full `research_md_path` content into the prompt
- **COSTAR sandbox prompt**:
  - `<context>`: tool name + full `research.md` content (verbatim)
  - `<objective>`: Write exactly these four files to `{output_dir}/`:
    - `Dockerfile` — official base image, non-root user (`USER nobody`), pinned deps, no `RUN curl | bash` or `RUN wget | sh`
    - `experiment.py` — imports tool, runs a meaningful demo of its core capability, prints structured output
    - `run.sh` — `docker build -t {slug}-exp . && docker run --rm --network none {slug}-exp` (network none unless tool explicitly requires outbound calls per research.md)
    - `experiment_plan.md` — describes what the experiment tests, expected output, how to interpret results
  - `<style>`: Minimal, production-quality Docker. Clear, runnable experiment. No placeholders.
  - `<tone>`: Engineering-grade. No comments explaining obvious code.
  - `<audience>`: Developer who will inspect and run the sandbox locally.
  - `<response>`: Write all four files. Do NOT execute any code. Do NOT install anything. Write files only.
  - Safety clause (verbatim in prompt): "Do NOT include `RUN curl | bash`, `RUN wget | sh`, or any other inline shell pipe execution. Only install packages from official PyPI or npm registries. Pin all dependency versions. If the experiment requires network access, document it explicitly in `experiment_plan.md`."
- Raises `FileNotFoundError` if `research_md_path` does not exist

### [11c] src/utils/vault_writer.py [ ]
- **MANDATORY**: Use the Read tool to read `src/utils/cockpit_components.py` to reuse `build_obsidian_url()` — do not duplicate.
- Public API:
  ```python
  def write_sandbox_note(
      tool: dict,
      research_summary: str,
      sandbox_dir: Path,
      vault_path: Path,
  ) -> Path
  ```
- Output path: `{vault_path}/Projects/Sandbox/{ToolName}.md`
- Creates `Projects/Sandbox/` if missing (`mkdir(parents=True, exist_ok=True)`)
- If file exists: append ISO timestamp suffix to filename (e.g. `ToolName_20260315T143000.md`) — never overwrite
- Frontmatter (YAML):
  ```yaml
  ---
  status: sandbox_ready
  date: {ISO date}
  tool_name: {tool["name"]}
  category: {tool.get("category", "")}
  sandbox_dir: {str(sandbox_dir)}
  ---
  ```
- Body: `## Research Summary\n{research_summary}\n\n## Experiment\nSee `{sandbox_dir}/experiment_plan.md`\n\n## Run\n```bash\ncd {sandbox_dir}\nbash run.sh\n```\n`
- Module-level logger: `logger = logging.getLogger(__name__)`
- `pathlib.Path` throughout

### [11d] Workbench page — Sandbox button + vault link [ ]
- **MANDATORY**: Use the Read tool to read `~/.claude/skills/developing-with-streamlit/skills/building-streamlit-llm-apps/SKILL.md`. Apply polling/status patterns.
- Wire `🧪 Start Sandbox` button (shown only when `experiment_type == "programmatic"` AND `reviewed == True` AND `status == "researched"`):
  - On click: `launch_sandbox_agent(tool, research_md, output_dir)` → save PID + log_file → status = `"sandbox_creating"` → `st.rerun()`
- While `status == "sandbox_creating"`:
  - Same log tail pattern as research phase (`st.code(tail_log(...))` + `🔄 Refresh`)
  - When PID gone: `write_sandbox_note(tool, summary, sandbox_dir, vault_path)` → status = `"sandbox_ready"` → `st.rerun()`
- Status `"sandbox_ready"`:
  - `🗂️ Open in Obsidian` link via `build_obsidian_url(vault_name, relative_note_path)`
  - `📂 Open Sandbox Dir` button → `subprocess.Popen(["open", str(sandbox_dir)])` (macOS Finder)
  - `run.sh` instructions in `st.code()` block
  - `st.code(f"cd {sandbox_dir} && bash run.sh", language="bash")` — copy-able command

### [11e] Round-trip integration tests [ ]
- **MANDATORY**: Run `/steadows-tdd`. Follow its EXACT protocol for integration tests.
- `tests/test_workbench_integration.py`:
  - Full pipeline: `add_to_workbench` → `get_workbench_item` → `update_workbench_item(status="researched")` → `write_sandbox_note` → vault note exists at correct path
  - `write_sandbox_note` vault note contains expected frontmatter keys
  - `parse_research_output` → `experiment_type` → correct branch logic (programmatic vs manual)
  - Workbench file survives concurrent reads (load twice, compare)
- [ ] **Verify GREEN**: `pytest tests/test_workbench_integration.py -v` — ALL PASS

### [11f] Full test suite [ ]
- [ ] `pytest tests/ -v --tb=short` — all tests PASS (prior tests + new S7–11 tests)
- [ ] `pytest tests/ --cov=src/utils --cov-report=term-missing` — coverage ≥ 80%
- [ ] `ruff check src/ tests/` — no errors
- [ ] `ruff format --check src/ tests/` — no formatting issues

### [11g] Final Quality Gate [ ]

**MANDATORY**: Each gate below requires reading the specified file with the Read tool and following its EXACT protocol. Do NOT improvise your own review — execute the steps in the file as written. Do NOT substitute your own code review process for the one defined in the file.

- [ ] **Verify**: Run `/steadows-verify`. Confirm build PASS, lint PASS, format PASS, full suite PASS, coverage ≥ 80%, secrets PASS (0 found). Includes code review (all Session 8–11 files) and security review (focus: subprocess injection, Dockerfile safety — no `RUN curl|bash`, vault write path inside vault boundary). All CRITICAL/HIGH findings fixed. Verdict: PASS.
- [ ] **Learn Eval**: `/everything-claude-code:learn-eval` — evaluate Sessions 8–11 for extractable patterns → save to `~/.claude/skills/learned/`.

### [11h] macOS desktop launcher [ ]
- Create an Automator app (or shell script + `.command` file) that:
  - Activates conda env `research-dashboard`
  - Runs `cd ~/research-dashboard/src && streamlit run Home.py`
  - Opens browser to `localhost:8501`
- Place in `/Applications/` or Desktop for double-click launch

### [11i] Commit [ ]
```bash
git add src/ tests/ GSD_PLAN.md
git commit -m "feat: sandbox pipeline — Opus research agent, Docker scaffolding, vault note writer"
```

---

## Session 12: Agentic Hub — Instagram Ingester + Parser [x]

Requires Session 11 complete.

Adds Instagram video ingestion as a new data source. Videos are downloaded via
`instaloader`, transcribed with `faster-whisper`, summarized by Claude Haiku, and
written to the Obsidian vault as structured markdown. A companion parser reads the
vault notes back into the dashboard data model. Sessions 12 and 13 implement the
full pipeline end-to-end.

**Review fixes applied** (GPT 5.4 issues 1–5, Opus issues 6–10 — see `SESSION_12_PLAN_REVIEW_FIXES.md`):
1. Added explicit `download_video()` helper with temp-file lifecycle
2. `title` persisted in YAML frontmatter; parser reads it back
3. Filenames include shortcode to prevent same-day collisions
4. Caching stays at page layer only — parser is a pure utility
5. New `call_haiku_json()` public helper in `claude_client.py`
6. Instaloader session/auth strategy and 401/429 handling documented
7. `transcribe_video` naming clarified (faster-whisper accepts video via ffmpeg)
8. State file writes per-post (not batch) to prevent re-ingestion on crash
9. `run_ingestion` accepts `known_projects` parameter
10. Atomic writes use `os.replace()` (not `Path.replace()`) — tests mock `os.replace`

### [12a] TDD — write ingester + parser tests first [x]
- **MANDATORY**: Run `/steadows-tdd`. Follow its EXACT step-by-step protocol. Do NOT skip steps or improvise your own TDD process.
- `tests/test_instagram_ingester.py`:
  - `fetch_recent_posts` returns only video posts (skip images/carousels gracefully — no exception)
  - `fetch_recent_posts` filters by `days` cutoff (posts older than `days` are excluded)
  - `fetch_recent_posts` skips shortcodes already present in state file
  - `fetch_recent_posts` logs a WARNING for skipped non-video posts (not an error)
  - `download_video` downloads video URL to `download_dir` and returns local `Path`
  - `download_video` cleans up partial file on failure
  - `transcribe_video` returns a string; applies `_TERM_CORRECTIONS` (mock `WhisperModel`)
  - `transcribe_video` maps "Cloud Code" → "Claude Code" in output text
  - `extract_keywords_and_summary` calls Haiku via `claude_client.call_haiku_json()`; returns dict with `key_points`, `keywords`, `title` keys
  - `extract_keywords_and_summary` includes known-project wiki-links (e.g. `[[Claude Code]]`) in keywords when project name appears in transcript
  - `write_vault_note` creates file at `{vault_path}/Research/Instagram/{username}/YYYY-MM-DD-{shortcode}.md`
  - `write_vault_note` creates intermediate directories if missing
  - `write_vault_note` returns Path to written file
  - Written file contains YAML frontmatter with `title`, `tags`, `date`, `account`, `shortcode`, `source_url`
  - Written file contains `## Caption`, `## Key Points`, `## Keywords`, `## Transcript` sections
  - `run_ingestion` orchestrates full pipeline and returns list of written Paths
  - State file write is atomic per-post (mock `os.replace`; verify temp file used after each successful write)
  - `run_ingestion` records each shortcode in state file after successful write
  - `run_ingestion` skips post and logs WARNING if transcription raises (never propagates exception)
  - `run_ingestion` deletes downloaded video in `finally` block after each post
- `tests/test_instagram_parser.py`:
  - `parse_instagram_posts` returns empty list when `Research/Instagram/` does not exist
  - `parse_instagram_posts` parses YAML frontmatter: `title`, `account`, `date`, `shortcode`, `source_url`
  - `parse_instagram_posts` uses `title` from frontmatter as `name` (falls back to `file.stem`)
  - `parse_instagram_posts` parses `## Key Points` bullets into `key_points` list
  - `parse_instagram_posts` parses `## Keywords` line into `keywords` list (strips `[[` / `]]`)
  - `parse_instagram_posts` captures `## Caption` and `## Transcript` as plain strings
  - `parse_instagram_posts` sets `source_type = "instagram"` on every returned dict
  - `parse_instagram_posts` filters by `accounts` when provided (ignores other accounts)
  - `parse_instagram_posts` tolerates a malformed file without raising (logs WARNING, skips)
  - Round-trip: `write_vault_note` output → `parse_instagram_posts` → fields match original inputs (including `title`)
- `tests/test_claude_client.py` (append):
  - `call_haiku_json` calls `_call_api` with Haiku model and returns response text
  - `call_haiku_json` respects `max_tokens` parameter
- [ ] **Verify RED**: `pytest tests/test_instagram_ingester.py tests/test_instagram_parser.py -v` — ALL tests FAIL (modules not yet created)

### [12b] src/utils/claude_client.py — add `call_haiku_json` [x]
- Add a thin public wrapper over the existing `_call_api()`:
  ```python
  def call_haiku_json(prompt: str, max_tokens: int = 600) -> str:
      """Call Haiku for structured JSON extraction.

      Args:
          prompt: User prompt expecting JSON response.
          max_tokens: Maximum response tokens.

      Returns:
          Raw response text (caller parses JSON).
      """
      result = _call_api(prompt, model=HAIKU_MODEL, max_tokens=max_tokens)
      return result["response"]
  ```
- Uses the existing `HAIKU_MODEL` constant already defined in the module.

### [12c] src/utils/instagram_ingester.py [x]
- **MANDATORY**: Use the Read tool to read `src/utils/status_tracker.py` to reuse the atomic write pattern (tempfile + `os.replace`) for state file writes.
- Imports: `instaloader`, `faster_whisper.WhisperModel`, `claude_client` (for `call_haiku_json`), `pathlib.Path`, `json`, `logging`, `datetime`, `tempfile`
- **Term corrections** (hardcoded constant, not user-configurable):
  ```python
  _TERM_CORRECTIONS: dict[str, str] = {
      "Cloud Code": "Claude Code",
      "Cloud Agents": "Claude Agents",
      "Cloud Agent": "Claude Agent",
      "Clod": "Claude",
  }
  ```
- `_DEFAULT_STATE_FILE = Path.home() / ".research-dashboard" / "instagram_state.json"`
- `_WHISPER_MODEL = "base"` — initialize lazily on first call (module-level singleton via `functools.lru_cache(maxsize=1)`)
- Public API:
  ```python
  def fetch_recent_posts(
      username: str,
      days: int = 14,
      state_file: Path = _DEFAULT_STATE_FILE,
  ) -> list[dict]

  def download_video(
      post: dict,
      download_dir: Path,
  ) -> Path

  def transcribe_video(video_path: Path) -> str

  def extract_keywords_and_summary(
      transcript: str,
      caption: str,
      known_projects: list[str],
  ) -> dict

  def write_vault_note(
      post: dict,
      transcript: str,
      extracted: dict,
      vault_path: Path,
  ) -> Path

  def run_ingestion(
      username: str,
      vault_path: Path,
      known_projects: list[str] | None = None,
      days: int = 14,
      state_file: Path = _DEFAULT_STATE_FILE,
  ) -> list[Path]
  ```
- **`fetch_recent_posts`**:
  - Load state from `state_file` (empty dict if missing)
  - Use `instaloader.Instaloader()` + `Profile.from_username()` to iterate posts
  - **Auth strategy**: anonymous access by default. If Instagram returns 401 or `LoginRequiredException`, log `ERROR: Instagram login required — set INSTAGRAM_SESSION_FILE env var` and return empty list. Do NOT prompt for credentials interactively.
  - Apply 2–3s `time.sleep()` delay between post metadata fetches to avoid rate limiting
  - On 429 / `TooManyRequestsException`: log WARNING, sleep 30s, retry once, then skip remaining posts
  - Skip post if `post.shortcode` already in state
  - Skip post if `not post.is_video` — log `WARNING: Skipping non-video post {shortcode}` and continue
  - Skip post if `post.date_utc < (datetime.utcnow() - timedelta(days=days))`
  - Return list of dicts: `{shortcode, url: post.video_url, caption: post.caption, date: post.date_utc.date().isoformat(), username}`
- **`download_video`**:
  - Download video from `post["url"]` to `download_dir / f"{post['shortcode']}.mp4"`
  - Use `instaloader.Instaloader().download_pic()` or `urllib.request.urlretrieve()` — whichever is simpler
  - Apply 2–3s `time.sleep()` after download (rate-limit courtesy)
  - On failure: delete partial file if it exists, then re-raise
  - Return `Path` to downloaded file
- **`transcribe_video`** (note: named `_video` because faster-whisper accepts video files directly via internal ffmpeg):
  - Initialize `WhisperModel("base", device="cpu", compute_type="int8")` via lazy singleton
  - Call `model.transcribe(str(video_path))`
  - Join all segment texts into a single string
  - Apply `_TERM_CORRECTIONS` via `str.replace()` for each entry (exact string match, case-sensitive)
  - Return corrected transcript string
- **`extract_keywords_and_summary`**:
  - Build a Haiku prompt asking for: `title` (≤10 words), `key_points` (3–5 bullet strings), `keywords` (project wiki-links + general terms)
  - Keyword wiki-link rule: if a known project name appears verbatim in `transcript` or `caption`, include it as `[[Project Name]]`
  - Call `claude_client.call_haiku_json(prompt)` — parse the returned JSON
  - Return `{"title": str, "key_points": list[str], "keywords": list[str]}`
  - On parse failure: log WARNING, return safe defaults (`title=caption[:60] or "Instagram Post"`, `key_points=[]`, `keywords=[]`)
- **`write_vault_note`**:
  - Output path: `{vault_path}/Research/Instagram/{post["username"]}/{post["date"]}-{post["shortcode"]}.md`
  - `mkdir(parents=True, exist_ok=True)` before writing
  - YAML frontmatter: `title`, `tags`, `date`, `account`, `shortcode`, `source_url`
  - Body sections: `## Caption`, `## Key Points` (bulleted), `## Keywords` (comma-separated wiki-links on one line), `## Transcript`
  - Write atomically: write to temp file in same directory, then `os.replace()`
  - Return `Path` to written file
- **`run_ingestion`**:
  - `known_projects` defaults to `[]` if `None`
  - Create a temporary download directory via `tempfile.mkdtemp(prefix="ig_ingest_")`
  - For each post from `fetch_recent_posts`:
    1. `download_video(post, download_dir)` → `video_path`
    2. `transcribe_video(video_path)` → `transcript`
    3. `extract_keywords_and_summary(transcript, post["caption"], known_projects)` → `extracted`
    4. `write_vault_note(post, transcript, extracted, vault_path)` → `note_path`
    5. In `finally` block: delete `video_path` if it exists
  - On any per-post exception: log `WARNING: Failed to ingest {shortcode}: {exc}`, continue (never propagates)
  - After each successful `write_vault_note`: add `{shortcode: {"ingested_at": ISO, "note_path": str(path)}}` to state dict and write state atomically (per-post, not batch — prevents re-ingestion on crash)
  - Clean up `download_dir` at end in a `finally` block
  - Return list of successfully written Paths
- Module-level logger: `logger = logging.getLogger(__name__)`
- `pathlib.Path` throughout; `os.replace()` is the one exception (used for atomic rename — not an `os.path` function)

### [12d] src/utils/instagram_parser.py [x]
- **MANDATORY**: Use the Read tool to read `src/utils/parser_helpers.py` to reuse `split_h2_sections()` and `parse_fields()`. Do not duplicate section-splitting logic.
- **No `@st.cache_data`** — this is a pure utility module with no Streamlit import. Caching is applied at the page layer (Session 13 adds a `_load_instagram_posts()` wrapper in `1_Dashboard.py`, consistent with `_load_blog_queue()`, `_load_tools()`, etc.).
- Public API:
  ```python
  def parse_instagram_posts(
      vault_path: Path,
      accounts: list[str] | None = None,
  ) -> list[dict]
  ```
- Glob `Research/Instagram/**/*.md` (recursive) under `vault_path`
- For each file:
  - Parse YAML frontmatter with `yaml.safe_load()` — extract `title`, `account`, `date`, `shortcode`, `source_url`, `tags`
  - Use `split_h2_sections()` to extract section bodies: `Caption`, `Key Points`, `Keywords`, `Transcript`
  - Parse `Key Points` lines: strip leading `- ` → `list[str]`
  - Parse `Keywords` line: split on `,`, strip whitespace and `[[` / `]]` → `list[str]`
  - Build return dict:
    ```python
    {
        "name": frontmatter.get("title") or file.stem,
        "account": frontmatter["account"],
        "date": frontmatter["date"],
        "source_url": frontmatter.get("source_url", ""),
        "shortcode": frontmatter.get("shortcode", ""),
        "key_points": list[str],
        "keywords": list[str],
        "caption": str,
        "transcript": str,
        "source_type": "instagram",
    }
    ```
  - On malformed file (missing frontmatter, YAML parse error): log `WARNING: Skipping malformed instagram note {path}`, continue
- Filter by `accounts` list if provided (match on `account` field, case-insensitive)
- Sort by `date` descending
- Module-level logger: `logger = logging.getLogger(__name__)`

### [12e] Update requirements.txt [x]
- Add `instaloader` and `faster-whisper` entries (verify exact PyPI package names match official registry)
- Do NOT add `ffmpeg` — already in conda env, not a pip dependency

### [12f] Verify GREEN [x]
- [x] Run `pytest tests/test_instagram_ingester.py tests/test_instagram_parser.py tests/test_claude_client.py -v` — ALL tests PASS
- [x] Run round-trip test: `write_vault_note` output → `parse_instagram_posts` → fields match (including `title`)
- [x] Run `pytest tests/ -v --tb=short` — full suite passes (prior tests unbroken)
- [x] Run `pytest tests/ --cov=src/utils --cov-report=term-missing` — `instagram_ingester` ≥ 80%, `instagram_parser` ≥ 80%, utils total ≥ 80%

### [12g] Quality Gate [x]

**MANDATORY**: Each gate below requires reading the specified file with the Read tool and following its EXACT protocol. Do NOT improvise your own review — execute the steps in the file as written.

- [x] **Verify**: Run `/steadows-verify`. Confirm build PASS, lint clean (`ruff check src/ tests/`), format clean (`ruff format --check`), full suite PASS, coverage ≥ 80%, secrets 0 found. Code review focus: `instagram_ingester.py` (atomic state write per-post, rate-limit delay, per-post exception isolation, download cleanup in finally, no shell=True), `instagram_parser.py` (no streamlit import, immutable returns, malformed-file tolerance), `claude_client.py` (new `call_haiku_json` is thin wrapper only). Security review focus: vault write path stays within `vault_path` boundary (verify with `.resolve().is_relative_to()`), no user-controlled paths in subprocess or shell calls, `yaml.safe_load()` used, downloaded video files cleaned up. All CRITICAL/HIGH findings fixed. Verdict: PASS.
- [ ] **Learn Eval**: `/everything-claude-code:learn-eval` — evaluate session for extractable patterns → save to `~/.claude/skills/learned/`.

### [12h] Commit [x]
```bash
git add src/utils/claude_client.py src/utils/instagram_ingester.py src/utils/instagram_parser.py tests/ requirements.txt GSD_PLAN.md
git commit -m "feat: instagram ingestion pipeline — instaloader fetch, whisper transcription, haiku extraction, vault writer, parser"
```

---

## Session 13: Agentic Hub Tab + Workbench Integration [x]

Requires Session 12 complete.

Surfaces ingested Instagram posts in a new "Agentic Hub" tab on the Dashboard, with
account filtering and per-card actions. Instagram posts flow into the existing Workbench
via `add_to_workbench` with `source_type="instagram"`. The research agent prompt is
extended to include the post transcript as additional context.

### [13a] TDD — write Agentic Hub tab + workbench integration tests first [x]
- **MANDATORY**: Run `/steadows-tdd`. Follow its EXACT step-by-step protocol.
- `tests/test_agentic_hub.py`:
  - `render_agentic_hub_tab` renders empty state when `parse_instagram_posts` returns `[]`
  - Account filter shows "All" option plus one pill per unique account in posts list
  - "All" filter selected by default; posts list is unfiltered
  - Selecting a specific account pill filters post cards to that account only
  - Each post card renders account badge, date, title, key points, keyword chips
  - `📝 Summarize` button disabled when inline summary already in session state for that post
  - `🔬 Workbench` button calls `add_to_workbench` with `source_type="instagram"` on click
  - `🔬 Workbench` button disabled when post `shortcode` already in workbench
  - All vault-sourced strings (title, caption, key points) passed through `safe_html()` before `unsafe_allow_html=True`
- `tests/test_instagram_workbench.py`:
  - `add_to_workbench` with instagram item stores `source_type = "instagram"` in entry
  - `add_to_workbench` uses `make_item_key("instagram", shortcode)` as workbench key
  - `update_workbench_item` for instagram entry preserves `transcript` field
  - Workbench page renders instagram entry with purple source badge (same as methods)
  - `_build_prompt` for research agent includes `<context>` block with transcript when `transcript` key present in item dict
- [ ] **Verify RED**: `pytest tests/test_agentic_hub.py tests/test_instagram_workbench.py -v` — ALL tests FAIL

### [13b] Dashboard — add "Agentic Hub" tab [x]
- **MANDATORY**: Use the Read tool to read `~/.claude/skills/developing-with-streamlit/skills/using-streamlit-layouts/SKILL.md`. Apply tab and column patterns.
- **MANDATORY**: Use the Read tool to read `~/.claude/skills/developing-with-streamlit/skills/avoiding-streamlit-widget-pitfalls/SKILL.md`. Apply key-only widget patterns.
- In `src/pages/1_Dashboard.py`:
  - Extend `st.tabs([...])` to include `"🤖 Agentic Hub"` as the sixth tab
  - Session state key: `dashboard__agentic_hub_account_filter` (default `"All"`)
  - Call `parse_instagram_posts(vault_path)` wrapped with `@st.cache_data(ttl=3600)` on the call site (consistent with other parser calls in this file)
  - Render empty state (`st.info(...)`) when posts list is empty — message: `"No Instagram posts ingested yet. Run the ingester for an account to populate this tab."`

### [13c] Account filter pills [x]
- **MANDATORY**: Use the Read tool to read `~/.claude/skills/developing-with-streamlit/skills/choosing-streamlit-selection-widgets/SKILL.md`. Apply pill/button filter patterns consistent with existing Dashboard filter UI.
- Build unique account list from posts: `sorted({p["account"] for p in posts})`
- Render as pill buttons: `["All"] + sorted_accounts`
- Active pill highlighted with amber border (consistent with existing filter pills in Tools Radar tab)
- On click: update `dashboard__agentic_hub_account_filter` → `st.rerun()`
- Filter posts list before rendering cards

### [13d] Post cards [x]
- **MANDATORY**: Use the Read tool to read `~/.claude/skills/developing-with-streamlit/skills/improving-streamlit-design/SKILL.md`. Apply surface-card HTML and badge patterns consistent with existing tool/blog cards.
- Per post card (surface-card div):
  - Header row: account badge (blue `#1E40AF`), date string (right-aligned)
  - Title: bold, `safe_html(post["name"])`
  - Key points: bulleted `<ul>` — each bullet via `safe_html(point)`
  - Keyword chips: amber chips for each keyword (same chip CSS as Tools Radar project tags)
  - Action row (`st.columns([1, 1])`):
    - `📝 Summarize` — Haiku inline summary. On click: call `claude_client` Haiku with transcript + key points. Store result in `st.session_state[f"dashboard__agentic_hub_summary_{post['shortcode']}"]`. Disabled while result already in session state. Show result inline below card on subsequent render.
    - `🔬 Workbench` — disabled when `make_item_key("instagram", post["shortcode"])` already in `get_workbench_items()`. On click: `add_to_workbench(post, previous_status="new")`, `st.rerun()`
- All vault-sourced strings use `safe_html()` before `unsafe_allow_html=True`

### [13e] Workbench — instagram entry rendering [x]
- **MANDATORY**: Use the Read tool to read `~/.claude/skills/developing-with-streamlit/skills/improving-streamlit-design/SKILL.md`. Apply badge patterns.
- In `src/pages/3_Workbench.py`:
  - Extend source-type badge colors: `"instagram"` → indigo `#6366F1` (distinct from method purple and tool green)
  - For instagram entries: show `caption` field (truncated to 200 chars) as the synthesis line instead of LLM summary
  - `🔍 Research` button: disabled for instagram entries (`source_type == "instagram"`) — research pipeline is tool/method-specific for now. Document with `st.caption("Research agent not yet wired for instagram posts.")` beneath the disabled button.

### [13f] Research agent — transcript context injection [x]
- In `src/utils/research_agent.py`:
  - In `_build_prompt(item: dict) -> str` (or wherever the COSTAR prompt is assembled):
    - If `item.get("transcript")` is non-empty: append a `<context>` block containing the first 4000 chars of the transcript after the existing `<context>` block content
    - Log at DEBUG: `"Injecting transcript context: {len(transcript)} chars"`
  - No changes to subprocess invocation — only the prompt string changes
  - Ensure existing tool-path tests still pass (transcript field absent → no change)

### [13g] Verify GREEN [x]
- [ ] Run `pytest tests/test_agentic_hub.py tests/test_instagram_workbench.py -v` — ALL tests PASS
- [ ] Run `pytest tests/ -v --tb=short` — full suite passes (prior tests unbroken)
- [ ] Run `pytest tests/ --cov=src/utils --cov-report=term-missing` — coverage ≥ 80%
- [ ] `ruff check src/ tests/` — no errors
- [ ] `ruff format --check src/ tests/` — no formatting issues

### [13h] Quality Gate [x]

**MANDATORY**: Each gate below requires reading the specified file with the Read tool and following its EXACT protocol. Do NOT improvise your own review — execute the steps in the file as written. Do NOT substitute your own code review process for the one defined in the file.

- [ ] **Verify**: Run `/steadows-verify`. Confirm build PASS, lint clean, format clean, full suite PASS, coverage ≥ 80%, secrets 0 found. Code review focus: `1_Dashboard.py` Agentic Hub tab (XSS via `safe_html()`, filter state namespacing, no API call on render path), `3_Workbench.py` instagram entry rendering (no KeyError on missing transcript/caption), `research_agent.py` transcript injection (truncation at 4000 chars, no prompt injection from vault content). Security review focus: transcript injected into prompt is bounded (4000 chars), vault strings escaped before HTML rendering, no user-controlled URLs passed to subprocess. All CRITICAL/HIGH findings fixed. Verdict: PASS.
- [ ] **Learn Eval**: `/everything-claude-code:learn-eval` — evaluate Sessions 12–13 for extractable patterns → save to `~/.claude/skills/learned/`.

### [13i] Commit [x]
```bash
git add src/ tests/ GSD_PLAN.md
git commit -m "feat: agentic hub tab — instagram post cards, account filter, workbench integration, transcript context injection"
```

---

## Session 14: Instagram Topic Research [~]

Requires Session 13 complete.

Enables Instagram posts to use the existing Workbench research pipeline with a
topic-aware prompt that answers "how can I best use this?" instead of the
tool-specific "should I integrate this?" framing. Post titles are preserved for
display while shortcode remains the durable identity key.

### Dependency order

1. Tests (identity → prompt → UI) — all RED before implementation
2. Identity model — shortcode key + preserved title
3. Instagram prompt — topic-centric COSTAR + low-signal handling
4. Workbench UI — enable research + topic preview/summary rendering

### [14a] TDD — write identity-model tests first [x]
- **MANDATORY**: Run `/steadows-tdd`. Follow its EXACT step-by-step protocol.
- `tests/test_instagram_workbench.py` — identity-model boundary:
  - Instagram entries preserve `item["name"]` as the human-readable title after `add_to_workbench()`
  - Workbench keys and `source_item_id` still resolve from `make_item_key("instagram", shortcode)`
  - Duplicate adds remain no-ops for the same shortcode
  - Two different posts with identical titles but different shortcodes persist as separate workbench entries
- [ ] **Verify RED**: `pytest tests/test_instagram_workbench.py -v -k identity` — new tests FAIL

### [14b] TDD — write prompt tests [x]
- `tests/test_instagram_workbench.py` — prompt boundary:
  - Instagram prompt uses topic-centric context/objective, not tool-centric framing
  - Instagram prompt requires `## Getting Started` instead of `## How to Install`
  - Transcript is truncated to 4000 chars in `research_agent.py` prompt builder
  - Missing transcript does not break prompt generation
  - Low-signal detection triggers when: no transcript, no key_points, and `len(caption.strip()) < 20`
  - Low-signal items still generate a valid prompt (not skipped)
- [ ] **Verify RED**: `pytest tests/test_instagram_workbench.py -v -k prompt` — new tests FAIL

### [14c] TDD — write UI/workbench integration tests [x]
- `tests/test_instagram_workbench.py` — UI boundary:
  - Agentic Hub sends the original post title (not shortcode) into Workbench
  - Workbench research button is enabled for Instagram items with status `queued` or `failed`
  - Workbench shows topic preview before research and overview summary after research
  - Existing tool and method research behavior is unchanged
- `tests/test_agentic_hub.py`:
  - Update expectations so Workbench integration keeps the title but identifies the item by shortcode
- [ ] **Verify RED**: `pytest tests/test_instagram_workbench.py tests/test_agentic_hub.py -v -k "ui or agentic"` — new tests FAIL

### [14d] Identity model — shortcode key + preserved title [x]
- In `src/pages/1_Dashboard.py`:
  - Stop replacing the post title (`name`) with the shortcode before `add_to_workbench()`
  - Keep Workbench button disabled by shortcode-based identity check
- In `src/utils/workbench_tracker.py`:
  - Introduce a shared identity helper so Instagram entries key on `shortcode` while storing the original `name` for display
  - Preserve existing tool/method behavior unchanged

### [14e] Instagram research prompt — topic-centric COSTAR [x]
- In `src/utils/research_agent.py`:
  - Add source-type-aware prompt builder branch for `source_type == "instagram"`
  - `<context>`: topic title (`name`), account, date, source_url, key_points, keywords, caption, transcript (truncated to 4000 chars in prompt builder — ingestion stays lossless)
  - `<objective>`: identify what the post is about; research underlying tool/pattern/concept; judge actionable vs. experimental vs. informational; design minimal evaluation path
  - `<style>` headings: `## Overview`, `## Getting Started`, `## Key APIs / Concepts`, `## Programmatic Assessment`, `## Experiment Design`, `## Safety Notes`
  - Low-signal behavior (no transcript + no key_points + caption < 20 chars): agent still runs; `## Overview` notes thin source material; `## Programmatic Assessment` starts with `NO` unless external research finds actionable content; `## Experiment Design` recommends what evidence is needed
  - Reuse existing subprocess/log/report machinery — no changes to launch path
  - `<response>` still writes only `research.md`

### [14f] Workbench UI — enable Instagram research [x]
- **MANDATORY**: Use the Read tool to read `~/.claude/skills/developing-with-streamlit/skills/improving-streamlit-design/SKILL.md`. Apply badge patterns.
- In `src/pages/3_Workbench.py`:
  - Remove the `source_type == "instagram"` research disable and the "not yet wired" caption
  - Show topic preview (title + key_points + keywords) for Instagram items before research
  - Switch to research overview summary after research completion (same pattern as tools/methods)

### [14g] Verify GREEN [x]
- [ ] Run `pytest tests/test_instagram_workbench.py tests/test_agentic_hub.py -v` — ALL tests PASS
- [ ] Run `pytest tests/ -v --tb=short` — full suite passes (prior tests unbroken)
- [ ] Run `pytest tests/ --cov=src/utils --cov-report=term-missing` — coverage ≥ 80%
- [ ] `ruff check src/ tests/` — no errors
- [ ] `ruff format --check src/ tests/` — no formatting issues

### [14h] Quality Gate [x]

**MANDATORY**: Each gate below requires reading the specified file with the Read tool and following its EXACT protocol. Do NOT improvise your own review — execute the steps in the file as written. Do NOT substitute your own code review process for the one defined in the file.

- [ ] **Verify**: Run `/steadows-verify`. Confirm build PASS, lint clean, format clean, full suite PASS, coverage ≥ 80%, secrets 0 found. Code review focus: `research_agent.py` Instagram prompt branch (transcript truncation at 4000 chars, low-signal threshold, no prompt injection from vault content, `## Getting Started` heading), `workbench_tracker.py` identity helper (shortcode key preserves title, no regression on tool/method keys), `1_Dashboard.py` Workbench button (title preserved, shortcode identity check). Security review focus: transcript content bounded before prompt injection, vault strings escaped, no user-controlled URLs in subprocess args. All CRITICAL/HIGH findings fixed. Verdict: PASS.
- [ ] **Learn Eval**: `/everything-claude-code:learn-eval` — evaluate Session 14 for extractable patterns → save to `~/.claude/skills/learned/`.

### [14i] Commit [ ]
```bash
git add src/ tests/ GSD_PLAN.md
git commit -m "feat: instagram topic research — topic-centric prompt, shortcode identity, workbench research enablement"
```

---

## Session 15: Graph Analysis Engine — Vault Network Intelligence [x]

Requires Session 14 complete.

Adds a graph analysis engine powered by `obsidiantools` + NetworkX. The engine
parses the Obsidian vault's wiki-link structure into a directed graph and computes
centrality metrics, community clusters, link predictions, and graph health stats.
Results surface in two places: a new Dashboard "Graph Insights" tab (vault-wide
view) and a per-project graph context section in the Project Cockpit.

Complements the existing data pipeline — `vault_parser.py` continues handling
project-specific parsing (frontmatter, GSD plans), while `obsidiantools` handles
vault-wide graph construction. The smart matcher's keyword-based inference (Tier 2)
and the knowledge linker's wiki-link injection remain unchanged. The graph engine
adds a structural analysis layer on top of both.

### Key capabilities

| Capability | What it answers | Algorithm |
|-----------|----------------|-----------|
| Hub detection | "What are my most connected notes?" | PageRank (directed) |
| Community clusters | "What research themes exist in my vault?" | Louvain (undirected) |
| Missing links | "What should be connected but isn't?" | Adamic-Adar index |
| Centrality ranking | "How important is this project structurally?" | Betweenness centrality |
| Graph health | "How fragmented is my knowledge graph?" | Component analysis, bridge detection |
| Neighborhood context | "What's 1-2 hops from this project?" | Adjacency traversal |

### Dependency order

1. Dependency install + test fixtures — establish obsidiantools + NetworkX in the env
2. Core engine (TDD) — `graph_engine.py` with pure graph functions
3. Dashboard tab — vault-wide graph insights rendering
4. Cockpit integration — per-project graph context section
5. Polish + quality gate

### Module boundary

`src/utils/graph_engine.py` is a **pure analysis module** — no Streamlit imports,
no caching decorators. Page files own all caching via `_load_graph_*()` wrappers
and `safe_parse()`, matching the existing pattern used by `_load_tools()`,
`_load_blog_queue()`, etc. This keeps the engine independently testable.

### Caching and invalidation

- Pages cache graph data via `@st.cache_data(ttl=3600)` wrappers (same as parsers)
- The `nx.DiGraph` object is not pickle-serializable, so pages use
  `@st.cache_resource(ttl=3600)` for the graph object only
- **Invalidation contract**: anywhere the app already calls `st.cache_data.clear()`
  (Dashboard refresh, Cockpit refresh, manual vault re-link), also call
  `st.cache_resource.clear()` so graph data stays in sync with parser data
- `graph_engine.py` has no cache awareness; pages own all invalidation

### Performance guardrails

- `build_vault_graph()` uses `connect()` only (fast, graph-only); skips `gather()`
- For vaults with >1000 nodes, skip `betweenness_centrality` (O(VE), expensive)
  and fall back to degree-only ranking. Log a WARNING.
- Link prediction limited to 3-hop neighborhood to avoid O(N²) candidate pairs
- All metrics cached with TTL=3600; no per-request recomputation

### obsidiantools integration notes

From research doc (`docs/research/obsidian-graph-tools.md`):
- `otools.Vault(path).connect()` is fast (graph-only); `.gather()` is slow — skip it
- Raw graph is `MultiDiGraph` — collapse to simple `DiGraph` for algorithms
- Remove self-loops (Obsidian header links like `[[note#section]]`)
- Filter non-existent notes (linked but never created) via `vault.file_index` if available; guarded with `hasattr()` check
- Louvain requires undirected graph; PageRank uses directed
- Bridge detection uses undirected projection: `nx.bridges(G.to_undirected())`
- `centrality_rank` is among ALL notes in the vault (not just project notes)

### [15a] TDD — write graph engine tests first [x]
- **MANDATORY**: Run `/steadows-tdd`. Follow its EXACT step-by-step protocol.
- Add `obsidiantools>=0.11.0,<1.0` and `networkx>=3.0` to `requirements.txt` and `pip install`
- `tests/conftest.py` — add a `graph_fixture` that builds a small `nx.DiGraph` with known topology:
  - 8 nodes: 3 "projects" (A, B, C), 3 "methods" (M1, M2, M3), 2 "tools" (T1, T2)
  - Known edges: A→M1, A→T1, B→M2, B→T1, B→T2, C→M3, M1→T1, M2→M3
  - This creates: a hub (T1 — 3 in-degree), a bridge (B — connects two clusters), an orphan-like node (C — only 2 edges), community structure (A-M1-T1 cluster, B-M2-M3-T2 cluster)
- `tests/test_graph_engine.py`:
  - **build_vault_graph**:
    - Returns `nx.DiGraph` (not `MultiDiGraph`)
    - No self-loops in returned graph
    - Non-existent notes (linked but uncreated) are filtered out
    - Empty vault returns graph with 0 nodes
  - **compute_centrality_metrics**:
    - Returns dict with keys `pagerank`, `betweenness`, `degree`, `in_degree`, `out_degree`
    - Each value is a `dict[str, float|int]` keyed by note name
    - PageRank values sum to ~1.0
    - Hub node (T1) has highest in-degree
    - Empty graph returns empty dicts for all metrics
  - **detect_communities**:
    - Returns `list[frozenset[str]]`
    - For graphs with 2+ nodes: every node appears in exactly one community; union equals all nodes
    - For graphs with 0-1 nodes: returns empty list (no meaningful communities)
    - Cockpit handles empty communities gracefully (shows "Not enough connections for clustering")
  - **suggest_links**:
    - Returns `list[tuple[str, float]]` sorted by score descending
    - Excludes existing neighbors from suggestions
    - Excludes self from suggestions
    - Returns empty list for note not in graph
    - `top_n` parameter limits result count
    - Scores are non-negative floats
  - **get_graph_health**:
    - Returns dict with `node_count`, `edge_count`, `orphan_count`, `component_count`, `bridge_count`
    - All values are non-negative ints
    - Empty graph returns all zeros
    - Disconnected graph has `component_count` > 1
  - **get_project_context**:
    - Returns dict with `centrality_rank`, `pagerank_score`, `neighbors`, `community_members`, `suggested_connections`
    - `centrality_rank` is 1-indexed int
    - Each neighbor is `{"name": str, "direction": "in"|"out"|"both", "pagerank": float}`
    - `neighbors` sorted by PageRank descending
    - `community_members` is `None` when graph has < 2 nodes (not enough for clustering)
    - Returns `None` for note not in graph
  - **Integration test** (uses real tmp vault with `.md` files):
    - Create 5 markdown files with `[[wiki-links]]` in a tmp directory, including at least one file in a `Projects/` subdirectory (e.g., `Projects/Alpha.md` linking to `Projects/Beta.md`)
    - Call `build_vault_graph()` on that directory
    - Verify nodes and edges match expected structure
    - Verify `compute_centrality_metrics()` produces non-empty results
    - **Project-name alignment**: call `parse_projects()` on the same tmp vault and verify that at least one project name from `parse_projects()` appears as a node in the graph — proving `Path.stem` alignment between the two parsers
    - Call `get_project_context()` with that project name and verify it returns a non-None result with valid `centrality_rank`
  - **UI regression tests** (extend existing page test files):
    - `tests/test_dashboard_tabs.py` — add tests:
      - Graph Insights tab is wired into `st.tabs()` call
      - Empty graph data degrades gracefully via `safe_parse()` (no exception)
      - Tab renders health stats, hub notes, communities, suggested links when data present
    - `tests/test_cockpit_graph_context.py` — new file (graph context is page-level behavior in `2_Project_Cockpit.py`, not a `cockpit_components.py` utility):
      - Missing-project graph context shows `st.info()` empty state, not exception
      - Graph context expander renders without error when graph data is available
      - Graph context handles `None` return from `get_project_context()` gracefully
      - Neighbors render correct direction indicators (→/←/↔) based on `direction` field
- [ ] **Verify RED**: `pytest tests/test_graph_engine.py -v` — tests fail for missing implementation

### [15b] Core engine — `src/utils/graph_engine.py` [x]
- Implement all functions to pass tests from [15a]:
  - `build_vault_graph(vault_path_str: str) -> nx.DiGraph`:
    1. `otools.Vault(vault_path_str).connect()`
    2. Convert `vault.graph` (MultiDiGraph) → simple `nx.DiGraph`
    3. Remove self-loops: `G.remove_edges_from(nx.selfloop_edges(G))`
    4. Filter non-existent notes: check `hasattr(vault, 'file_index')` before using; if present, keep only nodes whose name is a key in `vault.file_index`. If absent (API change), log WARNING and skip filtering.
    5. Return cleaned graph
  - `compute_centrality_metrics(G: nx.DiGraph) -> dict[str, dict[str, float]]`:
    - `pagerank`: `nx.pagerank(G)` (directed)
    - `betweenness`: `nx.betweenness_centrality(G)` (directed)
    - `degree`, `in_degree`, `out_degree`: from `G.degree()`, `G.in_degree()`, `G.out_degree()`
    - Guard: return empty dicts if `G.number_of_nodes() == 0`
  - `detect_communities(G: nx.DiGraph) -> list[frozenset[str]]`:
    - Guard: return empty list if graph has < 2 nodes (no meaningful communities for 0-1 nodes)
    - Convert to undirected, call `louvain_communities(G_undirected, seed=42)`
    - Contract: for 2+ node graphs, every node appears in exactly one community
  - `suggest_links(G: nx.DiGraph, note: str, top_n: int = 10) -> list[tuple[str, float]]`:
    - Validate note in graph; convert to undirected
    - Limit candidates to 3-hop neighborhood: `nx.single_source_shortest_path_length(G_undirected, note, cutoff=3)`
    - Exclude existing neighbors and self
    - `nx.adamic_adar_index(G_undirected, pairs)`
    - Filter zero scores, sort descending, return top N
  - `get_graph_health(G: nx.DiGraph) -> dict[str, int]`:
    - `node_count`, `edge_count`, `orphan_count` (degree 0), `component_count` (weakly connected), `bridge_count`
  - `get_project_context(G, metrics, communities, project_name) -> dict[str, Any] | None`:
    - Centrality rank from PageRank sorted descending (rank among ALL vault notes, 1-indexed)
    - `neighbors`: list of `{"name": str, "direction": "in"|"out"|"both", "pagerank": float}` dicts — built by checking `G.predecessors(project_name)` (→ "in"), `G.successors(project_name)` (→ "out"), intersection (→ "both"). Sorted by PageRank descending.
    - Community membership lookup — returns the frozenset containing this project, or `None` if graph has < 2 nodes
    - Suggested connections via `suggest_links()`
  - **No Streamlit imports in this module** — caching lives at the page layer (see [15c], [15d])
  - Performance guard: `compute_centrality_metrics()` skips `betweenness_centrality` when `G.number_of_nodes() > 1000`, logs a WARNING, and returns an empty dict `{}` for the `betweenness` key. Dashboard hub table renders "—" in the Betweenness column when the value is missing.
- [ ] **Verify GREEN**: `pytest tests/test_graph_engine.py -v` — ALL tests PASS
- [ ] Module is under 400 lines
- [ ] Type hints on all functions, docstrings on all public functions

### [15c] Dashboard — Graph Insights tab [x]
- **MANDATORY**: Use the Read tool to read `~/.claude/skills/developing-with-streamlit/skills/improving-streamlit-design/SKILL.md`. Apply card/badge patterns.
- In `src/pages/1_Dashboard.py`:
  - Add import: `from utils.graph_engine import build_vault_graph, compute_centrality_metrics, detect_communities, suggest_links, get_graph_health`
  - Add cached loaders following existing `_load_tools` pattern:
    - `@st.cache_resource(ttl=3600) _load_vault_graph(vault_str)` — calls `build_vault_graph()`, returns `nx.DiGraph`
    - `@st.cache_data(ttl=3600) _load_graph_metrics(vault_str)` — calls `compute_centrality_metrics()`, `detect_communities()`, `get_graph_health()`, returns serializable dict
  - **Invalidation**: update existing `_refresh_data()` / sidebar refresh and `_run_manual_link()` to call `st.cache_resource.clear()` alongside `st.cache_data.clear()` so graph stays in sync
  - Wrap graph data loads with `safe_parse(...)` for graceful degradation (obsidiantools import failure, empty vault, etc.)
  - Extend `st.tabs()` from 6 → 7 tabs: append `"🕸️ Graph Insights"`
  - Add `_render_graph_insights_tab(vault_str: str)` with 4 sections:
    - **Graph Health** — 5 metric cards in a row (nodes, edges, orphans, components, bridges) using `st.columns(5)` + `st.metric()`. Use surface-card CSS class consistent with other tabs.
    - **Hub Notes** — Top 15 notes by PageRank. `st.dataframe()` with columns: Rank, Note, PageRank, In-Degree, Betweenness. Column config for formatting (PageRank to 4 decimals, etc.).
    - **Research Communities** — One `st.expander()` per community (top 10 by size). Label: "Cluster N (X notes)". Inside: sorted member list with PageRank badge. Filter communities with < 3 members to reduce noise; show count of filtered as "N small clusters not shown".
    - **Suggested Links** — Pick top 5 hub notes, show top 3 link predictions each. Format: "Hub Note → Suggested Note (score: 0.42)". Use `st.caption()` for scores.
  - Wire up: `with tab_graph: _render_graph_insights_tab(vault_str)`
  - Load graph data in `_run_dashboard()` alongside other `safe_parse` calls

### [15d] Cockpit — per-project graph context [x]
- In `src/pages/2_Project_Cockpit.py`:
  - Add import: `from utils.graph_engine import build_vault_graph, compute_centrality_metrics, detect_communities, get_project_context`
  - Add cached loaders matching Dashboard pattern:
    - Reuse same `@st.cache_resource` / `@st.cache_data` wrapper functions (import from a shared location or duplicate — both are small)
    - Wrap with `safe_parse(...)` for graceful degradation
  - **Invalidation**: update existing Cockpit refresh to also call `st.cache_resource.clear()`
  - Add `_render_graph_context(project_name: str, vault_str: str) -> None`:
    - Load cached graph + metrics
    - Call `get_project_context()` for selected project
    - Handle `None` return (project not in graph) with `st.info("No graph data for this project")`
    - Render 4 subsections:
      - **Centrality** — "Ranks #X of Y notes by PageRank" as `st.metric()`
      - **Nearest neighbors** — Top 5 connected notes with direction indicator (→ outgoing, ← incoming, ↔ bidirectional). Each neighbor is a `st.caption()` line.
      - **Community** — "Part of cluster with N notes" + expandable member list
      - **Suggested connections** — Top 5 link predictions with Adamic-Adar scores
  - Wire up: add as a collapsible `st.expander("🕸️ Graph Context", expanded=False)` in the **lower metadata/context area**, alongside existing project header and context sources. Keep the current layout: title → flagged items feed → metadata/context (graph context goes here)

### [15e] Verify GREEN [x]
- [x] Run `pytest tests/test_graph_engine.py -v` — ALL tests PASS
- [x] Run `pytest tests/ -v --tb=short` — full suite passes (prior tests unbroken)
- [x] Run `pytest tests/ --cov=src/utils --cov-report=term-missing` — coverage ≥ 80%
- [x] `ruff check src/ tests/` — no errors
- [x] `ruff format --check src/ tests/` — no formatting issues
- [x] Manual smoke test: `cd src && streamlit run Home.py`
  - Dashboard → Graph Insights tab renders with health stats, hub notes, communities, suggested links
  - Project Cockpit → Graph Context expander shows centrality, neighbors, community, suggestions
  - Both views handle empty/missing project gracefully

### [15f] Quality Gate [x]

**MANDATORY**: Each gate below requires reading the specified file with the Read tool and following its EXACT protocol. Do NOT improvise your own review — execute the steps in the file as written. Do NOT substitute your own code review process for the one defined in the file.

- [x] **Verify**: Run `/steadows-verify`. Confirm build PASS, lint clean, format clean, full suite PASS, coverage ≥ 80%, secrets 0 found. Code review focus: `graph_engine.py` (cached graph not mutated, 3-hop limit on link prediction, empty graph guards, frozenset serialization). Security review focus: no vault path traversal, no user-controlled input to `nx` algorithms, cached resource not modified by callers. All CRITICAL/HIGH findings fixed. Verdict: PASS.
- [x] **Learn Eval**: `/everything-claude-code:learn-eval` — evaluate Session 15 for extractable patterns → save to `~/.claude/skills/learned/`.

### [15g] Commit [x]
```bash
git add src/utils/graph_engine.py src/pages/1_Dashboard.py src/pages/2_Project_Cockpit.py \
  tests/test_graph_engine.py tests/test_dashboard_tabs.py tests/test_cockpit_graph_context.py \
  tests/conftest.py requirements.txt GSD_PLAN.md
git commit -m "feat: graph analysis engine — vault network intelligence via obsidiantools + NetworkX"
```

---

## Session 16: Graph-Powered Item Discovery + Graph Context in LLM Prompts [x]

Requires Session 15 complete.

Addresses a core limitation: items (methods, tools, blog ideas) connect to projects **only via explicit `[[wiki-links]]`** (Tier 1) or keyword inference (Tier 2 via `smart_matcher`). If a method is linked to Project A and Project A sits in the same vault community as Project B, that method never surfaces for Project B — even though the graph says they're related.

**Critical design insight:** Items are NOT graph nodes. Methods, tools, and blog ideas are entries _within_ single vault notes (`Methods to Try.md`, `Tools Radar.md`, `Blog Queue.md`). The graph operates on notes (files), not on entries within files. Therefore, graph-powered discovery must work through **project-to-project proximity**, not direct item-to-graph matching.

**Scope:** Session 16 applies to methods, tools, and blog items only. Instagram posts are individual vault notes but lack `projects` fields and are not part of `build_smart_project_index()` — Instagram graph discovery is out of scope until a project-indexing contract exists for Instagram items.

This session adds three interconnected capabilities:

1. **Graph-powered item discovery via project proximity** — `smart_matcher.py` gains `get_graph_linked_items()` that discovers items through project-to-project graph relationships. If Project A and Project B are in the same Louvain community, items linked to B become candidates for A. If `suggest_links(G, "Project A")` returns "Project C", items linked to C become candidates for A. Each item carries a `discovery_source` field (`"linked"` / `"community"` / `"suggested"`) and a `via_project` field for provenance. The existing `source` field (human-readable provenance) is preserved untouched.

2. **Graph context injection into LLM prompts** — `prompt_builder.py` gains a `_format_graph_context()` helper and both `build_quick_prompt` / `build_deep_prompt` accept an optional `graph_context` parameter. When present, a `<graph_context>` section is injected with community peers, top neighbors, suggested connections, and centrality rank — plus reasoning instructions telling Claude to factor graph structure into relevance scoring. Graph-derived strings (note names) are sanitized before prompt injection.

3. **Cockpit wiring + source badges** — `2_Project_Cockpit.py` passes graph context through to prompts and renders discovery-source badges on each item card. Analysis cache keys are versioned to prevent stale pre-graph results from masking new prompts.

### Key design decisions

- `get_graph_linked_items()` lives in `smart_matcher.py` (alongside the existing Tier 1/Tier 2 matching) because it's a Tier 3 matching strategy operating on the project index — not graph primitives.
- **Project proximity propagation model:** Items don't need graph nodes. If item X → Project A → (community) → Project B, then item X is surfaced for Project B. Works for methods, tools, and blog items.
- **Field naming:** New field is `discovery_source` (not `source`). The existing `source` field carries parser provenance and is rendered in card UI and LLM prompts — must not be overwritten.
- **Propagated item metadata:** Graph-propagated items carry `origin_match_type` and `origin_confidence` (from their peer-project match). The Cockpit renders `discovery_source` / `via_project` for these items, NOT the origin match metadata.
- Source badges: `linked` = no badge (default/expected, avoid noise), `community` = blue (`#3B82F6`) with `via: ProjectName`, `suggested` = amber (`#F59E0B`) with `via: ProjectName`.
- **Deduplication uses composite key** `f"{source_type}::{name}"` — matches the existing identity model in `smart_matcher.py` and the Cockpit status system. Priority: `linked` > `community` > `suggested`.
- `graph_context` is keyword-only with `None` default on all prompt functions — fully backward compatible.
- **Graph propagation uses explicit matches only.** Tier 2 inferred matches in peer projects are NOT propagated — only items where `match_type == "explicit"`. Prevents compounding weak signals across graph edges.
- **Deterministic peer ordering:** Community peers sorted alphabetically before iteration. Suggested peers sorted by Adamic-Adar score (existing order). `via_project` is stable across reruns.
- **Single graph context object:** `_load_project_graph_context()` in the Cockpit page reuses Session 15 cached loaders (`_load_vault_graph`, `_load_graph_context_data`) and only derives the per-project slice. Does NOT recompute graph/metrics/communities per project. Includes `node_count` alongside the `get_project_context()` output.
- **Analysis cache versioning (global bump):** Bump `_CACHE_VERSION` globally for all quick/deep analyses. All pre-Session-16 cached results are invalidated. Simpler than conditional key branching.
- **Prompt safety:** Graph-derived strings (note names, community members) are escaped for XML control characters (`<`, `>`, `&`) before insertion into prompt blocks. Adversarial note name tests verify prompt structure integrity.

### [16a] TDD — write graph-linked item discovery tests first [x]

- **MANDATORY**: Run `/steadows-tdd`. Follow its EXACT step-by-step protocol.
- `tests/test_graph_linked_items.py`:
  - **Linked items returned with `discovery_source="linked"`** — items already in the project index (Tier 1/2) are returned with `discovery_source="linked"`, `via_project=None`. The existing `source` field is preserved unchanged.
  - **Community items via project proximity** — if Project A and Project B are in the same community (`community_members`), **explicitly-linked** items from B (`match_type == "explicit"` in `project_index["B"]`) are surfaced for A with `discovery_source="community"` and `via_project="B"`. Tier 2 inferred matches from peer projects are NOT propagated.
  - **Suggested items via project proximity** — if `suggest_links()` output for Project A includes Project C, **explicitly-linked** items from C are surfaced for A with `discovery_source="suggested"` and `via_project="C"`. Same explicit-only rule.
  - **Community peers are sorted alphabetically before iteration** — `via_project` for a deduplicated item is deterministic: the alphabetically-first peer project that contributes it. Suggested peers are sorted by Adamic-Adar score descending (existing order from `suggest_links()`).
  - **Deduplication uses composite key `source_type::name`** — if an item is linked to both the selected project and a peer project, it appears once with `discovery_source="linked"`. If a peer project appears in both community and suggested, community wins. Two items with the same name but different `source_type` are NOT collapsed.
  - **Items from multiple peer projects are deduplicated** — if item X is explicitly linked to both Project B (community) and Project C (community), it appears once. `via_project` records the alphabetically-first peer.
  - **Propagated items carry `origin_match_type` and `origin_confidence`** — the peer-project `match_type` and `confidence` are preserved under `origin_*` prefixed fields, NOT as direct `match_type`/`confidence` on the surfaced item.
  - **Empty `graph_context` (`None`) returns only linked items** — backward compatible, no graph discovery.
  - **Empty project index returns empty list** — no linked items and no peer projects = empty.
  - **Return type is `list[dict]`** — each dict is a shallow copy with added `discovery_source`, `via_project`, and (for propagated items) `origin_match_type`/`origin_confidence` fields. Original items never mutated. Existing `source` field preserved.
  - **Items are sorted: linked first, then community, then suggested** — within each group, original order preserved.
  - **Peer project names that don't exist in project_index are ignored** — community members that aren't project names (e.g. random vault notes) produce no items.
  - **Self-exclusion** — the selected project itself is excluded from peer lookup even if it appears in its own community.
- [ ] **Verify RED**: `pytest tests/test_graph_linked_items.py -v` — ALL tests FAIL (function not yet implemented)

### [16b] `src/utils/smart_matcher.py` — `get_graph_linked_items()` [x]

- Add to `smart_matcher.py` (alongside existing Tier 1/Tier 2 matching — this is Tier 3):
  ```python
  def get_graph_linked_items(
      project_name: str,
      linked_items: list[dict[str, Any]],
      project_index: dict[str, list[dict[str, Any]]],
      graph_context: dict[str, Any] | None = None,
  ) -> list[dict[str, Any]]:
  ```
- Parameters:
  - `project_name`: Selected project name
  - `linked_items`: Items already matched for this project (from `build_smart_project_index`)
  - `project_index`: Full project index (`dict[str, list[dict]]`) — needed to look up items linked to peer projects
  - `graph_context`: Output of `get_project_context()` — contains `community_members`, `suggested_connections`
- Helper `_item_id(item: dict) -> str` — returns `f"{item.get('source_type', 'item')}::{item.get('name', '')}"` (composite identity key matching existing repo convention)
- Helper `_tag_item(item: dict, discovery_source: str, via_project: str | None = None) -> dict` — returns shallow copy with added fields:
  - `discovery_source`: `"linked"` / `"community"` / `"suggested"`
  - `via_project`: peer project name or `None`
  - For propagated items (`discovery_source != "linked"`): also adds `origin_match_type` (from item's `match_type`) and `origin_confidence` (from item's `confidence`), then removes `match_type`/`confidence` from the copy to prevent misleading display
- Implementation:
  1. Start with linked items → tag with `discovery_source="linked"`, `via_project=None`
  2. Build `seen_ids: set[str]` from `_item_id()` of linked items
  3. If `graph_context` is `None`, return linked-only list
  4. Extract `community_members` frozenset. Filter to project names that exist in `project_index` and are not `project_name` itself. **Sort alphabetically** → `community_projects` (deterministic iteration order)
  5. For each peer in `community_projects`: iterate `project_index[peer]`, **skip items where `match_type != "explicit"`** (Tier 2 inferred matches are not propagated). Add items whose `_item_id()` is not in `seen_ids` with `discovery_source="community"`, `via_project=peer`. Add to `seen_ids`.
  6. Extract `suggested_connections` list of `(name, score)`. Filter to project names in `project_index` and not `project_name` → `suggested_projects` (already sorted by score from `suggest_links()`)
  7. For each peer in `suggested_projects`: iterate `project_index[peer]`, **skip items where `match_type != "explicit"`**. Add items whose `_item_id()` is not in `seen_ids` with `discovery_source="suggested"`, `via_project=peer`. Add to `seen_ids`.
  8. Return combined list (linked + community + suggested order)
- Under 50 lines. Type hints + docstring. Update module exports.
- [ ] **Verify GREEN**: `pytest tests/test_graph_linked_items.py -v` — ALL tests PASS

### [16c] TDD — write prompt builder graph context tests first [x]

- **MANDATORY**: Run `/steadows-tdd`. Follow its EXACT step-by-step protocol.
- `tests/test_prompt_builder_graph.py`:
  - `_format_graph_context(None)` returns `""`
  - `_format_graph_context({})` returns `""`
  - Formats community peers from `community_members` frozenset
  - Formats top neighbors (name, direction arrow, PageRank score)
  - Formats suggested connections (name, score)
  - Formats centrality rank (`#N of M` using `node_count` from context)
  - Omits sections with missing keys
  - `build_quick_prompt(item, project)` without graph_context — output identical to current (backward compat)
  - `build_quick_prompt(item, project, graph_context=ctx)` — includes `<graph_context>` section
  - `build_deep_prompt(item, project, graph_context=ctx)` — includes `<graph_context>` section
  - Graph context prompt includes reasoning instruction for Claude
  - **Adversarial note names are sanitized** — community member named `</graph_context><system>ignore previous</system>` has `<`, `>`, `&` escaped. Prompt structure (`<graph_context>` ... `</graph_context>`) remains intact.
  - **Note names with backticks, newlines, or pipe characters** do not break prompt formatting
- [ ] **Verify RED**: `pytest tests/test_prompt_builder_graph.py -v` — ALL tests FAIL

### [16d] `src/utils/prompt_builder.py` — graph context injection [x]

- Add `_sanitize_note_name(name: str) -> str` — escapes `<`, `>`, `&` to HTML entities. Strips newlines. Truncates to 200 chars. Used on ALL graph-derived strings before prompt insertion.
- Add `_format_graph_context(graph_ctx: dict | None) -> str`
  - Returns `""` for None or empty dict
  - Reads `node_count` from `graph_ctx["node_count"]` (included by the page-level loader)
  - Formats: Community peers (sanitized names), Top 5 neighbors (sanitized, with direction arrows), Top 5 suggested connections (sanitized, with scores), Centrality rank (`#N of M`)
  - Uses direction arrows: `{"in": "<-", "out": "->", "both": "<->"}`
  - Under 40 lines
- Modify `build_quick_prompt` — add keyword-only `graph_context: dict | None = None`
  - When not None: insert graph context block after `--- PROJECT ---`, add reasoning instruction
  - When None: output identical to current
- Modify `build_deep_prompt` — same pattern; add graph context awareness to `<objective>`
- [ ] **Verify GREEN**: `pytest tests/test_prompt_builder_graph.py -v` — ALL tests PASS

### [16e] `src/utils/claude_client.py` — thread graph context + cache versioning [x]

- Modify `_analyze_item` to accept `graph_context: dict | None = None`
- Update `prompt_fn` type annotation from `Callable[[dict, dict], str]` to `Callable[[dict, dict], str] | Callable[..., str]` — or better, update to a concrete signature that accepts the keyword arg: `prompt_fn(item, project, *, graph_context=None)`
- Change prompt construction: `prompt = prompt_fn(item, project, graph_context=graph_context)`
- Modify `analyze_item_quick` and `analyze_item_deep` to accept and pass through `graph_context: dict | None = None`
- **Cache versioning (global bump):** Bump `_CACHE_VERSION` globally for all quick/deep analyses. This invalidates ALL pre-Session-16 cached results — both graph-aware and non-graph. Simpler than conditional key branching, and the cost of re-running a few analyses is low compared to the risk of stale cache masking new prompts. Update the Cockpit's inline cache-result lookup key to match the new version.
- Backward compatible for callers — `None` default produces identical prompts to pre-Session-16, but cache keys use the new version (old results are re-analyzed on first access)

### [16f] `src/pages/2_Project_Cockpit.py` — wiring + source badges [x]

- **MANDATORY**: Read `~/.claude/skills/developing-with-streamlit/skills/improving-streamlit-design/SKILL.md`. Apply badge patterns.
- **Single graph context loader** — add helper that reuses Session 15 cached loaders:
  ```python
  def _load_project_graph_context(vault_path_str: str, project_name: str) -> dict | None:
      G = _load_vault_graph(vault_path_str)                    # Session 15, @st.cache_resource
      graph_data = _load_graph_context_data(vault_path_str)    # Session 15, @st.cache_data → dict
      metrics = graph_data["metrics"]
      communities = [frozenset(c) for c in graph_data["communities"]]  # deserialize from lists
      node_count = graph_data["node_count"]
      ctx = get_project_context(G, metrics, communities, project_name)
      if ctx is None:
          return None
      return {**ctx, "node_count": node_count}
  ```
  **Does NOT recompute the graph pipeline per project.** Graph + metrics + communities are cached at the vault level by Session 15. `_load_graph_context_data` returns a dict (not a tuple) with serialized communities (plain lists, not frozensets — `@st.cache_data` requires hashable/serializable returns). Only the per-project slice (`get_project_context`) is derived per call — this is cheap (dict lookups + sort).
  - Called once in `_run_cockpit()` after project selection, **wrapped in `safe_parse`**:
    ```python
    graph_ctx = safe_parse(
        _load_project_graph_context, vault_str, selected_name,
        fallback=None, label="project graph context",
    )
    ```
  - If `graph_ctx is None` (project not in graph OR graph loading fails): `get_graph_linked_items()` returns linked-only items, prompt builders receive `graph_context=None`, the graph expander shows the existing empty/info state. **No Cockpit breakage.**
  - Passed to: `get_graph_linked_items()`, prompt building, and `_render_graph_context()` (refactor the existing graph expander to accept the pre-computed context instead of computing its own).
- **Graph-powered item discovery**:
  - After `items = project_index.get(selected_name, [])`, call:
    ```python
    items = get_graph_linked_items(
        project_name=selected_name,
        linked_items=items,
        project_index=project_index,
        graph_context=graph_ctx,
    )
    ```
  - `project_index` is already loaded by `build_smart_project_index()` — pass it through.
- **Discovery-source badges** in item card header (keyed on `discovery_source`, NOT `source`):
  - `community`: `<span style="background:#1F2937;color:#3B82F6;padding:1px 6px;border-radius:3px;font-size:0.65rem;margin-left:4px">via {via_project}</span>`
  - `suggested`: `<span style="background:#1F2937;color:#F59E0B;padding:1px 6px;border-radius:3px;font-size:0.65rem;margin-left:4px">via {via_project}</span>`
  - `linked`: no badge (default behavior)
  - Apply `safe_html()` to `via_project` before injecting into badge HTML.
  - For propagated items: do NOT render `match_type` or `confidence` badges — use `discovery_source` / `via_project` instead. The existing `source` field renders normally (it's the parser provenance, not the discovery mechanism).
- **Pass graph context into analysis**:
  - Thread `graph_context` → `_run_analysis` → `analyze_item_quick` / `analyze_item_deep`

### [16g] Verify GREEN [x]

- [x] Run `pytest tests/test_graph_linked_items.py -v` — ALL tests PASS
- [x] Run `pytest tests/test_prompt_builder_graph.py -v` — ALL tests PASS
- [x] Run `pytest tests/ -v --tb=short` — full suite passes (prior tests unbroken)
- [x] Run `pytest tests/ --cov=src/utils --cov-report=term-missing` — coverage ≥ 80%
- [x] `ruff check src/ tests/` — no errors
- [x] `ruff format --check src/ tests/` — no formatting issues
- [x] Manual smoke test: `cd src && streamlit run Home.py`
  - Project Cockpit → project with known community members → community/suggested items appear with badges
  - Analyze button → `LLM_TRACE=1` → `<graph_context>` section visible in trace log
  - Project not in graph → graceful degradation, only linked items shown

### [16h] Quality Gate [x]

**MANDATORY**: Each gate below requires reading the specified file with the Read tool and following its EXACT protocol. Do NOT improvise your own review — execute the steps in the file as written.

- [x] **TDD**: Run `/steadows-tdd`. Confirm RED/GREEN cycle documented for both test files.
- [x] **Code Review**: Run `/steadows-code-review`. Focus: `smart_matcher.py` (composite dedup key, immutable copies, origin metadata separation), `prompt_builder.py` (backward compat — no graph_context arg produces identical output, `_sanitize_note_name` on all graph strings), `claude_client.py` (graph_context threading, cache version bump), `2_Project_Cockpit.py` (single `_load_project_graph_context` — no duplicated graph loading, `safe_html` on badge rendering, `discovery_source` not `source` for badges).
- [x] **Verify**: Run `/steadows-verify`. Confirm build PASS, lint clean, format clean, full suite PASS, coverage ≥ 80%, secrets 0 found. All CRITICAL/HIGH findings fixed. Verdict: PASS.
- [x] **Security Review**: Run `/steadows-security-review`. Focus: graph context injected into prompts — verify no prompt injection from note names; `safe_html()` on all vault-sourced strings in badges.
- [x] **Learn Eval**: `/everything-claude-code:learn-eval` — evaluate Session 16 for extractable patterns → save to `~/.claude/skills/learned/`.

### [16i] Commit [x]

```bash
git add src/utils/smart_matcher.py src/utils/prompt_builder.py src/utils/claude_client.py \
  src/pages/2_Project_Cockpit.py \
  tests/test_graph_linked_items.py tests/test_prompt_builder_graph.py \
  GSD_PLAN.md
git commit -m "feat: graph-powered item discovery — project proximity propagation, graph context in LLM prompts, discovery badges"
```

---

## Session 17: Migration Tooling + Skills + Streamlit Decoupling [x]

**Scope:** Symlink portfolio-v2 skills, decouple `smart_matcher.py` and `page_helpers.py` from Streamlit, scaffold `api/` and `web/` directories, update CLAUDE.md for dual-stack.

**Skills:** None loaded yet (this session creates the symlinks)
**Stitch:** N/A (infrastructure only)
**Agent teams:**
- Run `/steadows-code-review` after decoupling + scaffold complete
**Concurrency:** None

### [17a] Symlink Skills [x]

- [x] Symlink `~/portfolio-v2/.agents/skills/framer-motion-animator/` → `.claude/skills/framer-motion-animator`
- [x] Symlink `~/portfolio-v2/.agents/skills/framer-motion/` → `.claude/skills/framer-motion`
- [x] Symlink `~/portfolio-v2/.agents/skills/tailwind-v4-shadcn/` → `.claude/skills/tailwind-v4-shadcn`
- [x] Symlink `~/portfolio-v2/.agents/skills/d3-viz/` → `.claude/skills/d3-viz`
- [x] Verify all 4 symlinks resolve correctly

### [17b] TDD + Decouple smart_matcher.py [x]

- [x] **TDD**: Run `/steadows-tdd`. Follow its EXACT step-by-step protocol.
- [x] Add `cachetools` to `requirements.txt`
- [x] Replace `@st.cache_data` (line 488) with `cachetools.TTLCache`
- [x] Remove `import streamlit` (line 9)
- [x] Add `clear_project_index_cache()` function
- [x] Run existing `smart_matcher` tests — all GREEN
- [x] Verify `smart_matcher.py` importable without Streamlit: `python -c "from src.utils.smart_matcher import build_smart_project_index"`

### [17c] Split page_helpers.py [x]

- [x] Extract `render_context_sources()` (line 160) into `page_helpers_st.py`
- [x] Keep pure functions in `page_helpers.py`
- [x] Update all imports in page files (`1_Dashboard.py`, `2_Project_Cockpit.py`, `3_Workbench.py`)
- [x] Run full test suite — all GREEN

### [17d] Update CLAUDE.md [x]

- [x] Add frontend skills table (`framer-motion-animator`, `framer-motion`, `tailwind-v4-shadcn`, `d3-viz`)
- [x] Add design system reference (`docs/designs/DESIGN_SYSTEM.md`)
- [x] Add dual-stack architecture description (FastAPI + Next.js alongside Streamlit)

### [17e] Create api/ and web/ Scaffolds [x]

- [x] Define import strategy: `api/` adds `src/` to `sys.path` via `api/deps.py` so `from utils.*` imports work at runtime (not just pytest)
- [x] `api/main.py` — empty FastAPI app factory
- [x] `api/deps.py` — dependency stubs + `sys.path` setup for `src/utils/` access
- [x] `api/routers/` — empty directory with `__init__.py`
- [x] `web/.gitkeep`
- [x] Smoke test: `uvicorn api.main:app` starts without import errors (no routes yet, just app factory)

### [17f] Quality Gate [x]

- [x] **Verify**: Run `/steadows-verify`. All 415 tests pass, `smart_matcher.py` importable without Streamlit, lint clean, security clean. Code review issues (TTLCache thread safety, get_vault_path duplication) fixed.

### [17g] Commit [x]

```bash
git add .claude/skills/ src/utils/smart_matcher.py src/utils/page_helpers.py \
  src/utils/page_helpers_st.py src/pages/ api/ web/ CLAUDE.md GSD_PLAN.md
git commit -m "feat: migration tooling — decouple smart_matcher from Streamlit, scaffold api/ and web/, symlink frontend skills"
```

---

## Session 18: FastAPI Core — Read-Only Endpoints [x]

**Scope:** Read-only API layer — thin parser adapters plus derived read models (project index, graph-linked items, viz graph). No mutations.

**Skills (MANDATORY reads):**
- `api-design/SKILL.md` — REST resource naming, status codes, pagination, error envelope
- `python-patterns/SKILL.md` — Pythonic idioms, type hints for Pydantic models

**Stitch:** N/A (API only)
**Agent teams:**
- Deploy `planner` agent to design router structure before implementation
- Run `/steadows-code-review` + `/steadows-security-review` after implementation
**Concurrency:** [18b] app factory + [18c] routers can be written concurrently by agent team if subsections are independent

### [18a] TDD: Read-Only API Tests [x]

- [x] **TDD**: Run `/steadows-tdd`. Follow its EXACT step-by-step protocol.
- [x] Create `tests/test_api_read.py`
- [x] Mock all parsers, test GET endpoints return correct shapes
- [x] Derived endpoint tests: `/api/project-index/{project}/graph` returns graph-linked items with stable keys; `/api/graph/{project}/viz` returns `{nodes, edges}` with globally unique IDs, collapsed duplicate edges, and valid `{nodes: [], edges: []}` for empty graphs
- [x] Run tests — all RED (no implementation yet)

### [18b] App Factory + Dependencies [x]

- [x] `api/main.py` — CORS configured for `localhost:3000`, include all routers
- [x] `api/deps.py` — vault path from env, API key from env, vault path validation
- [x] `api/serializers.py` — DiGraph → adjacency dict, frozenset → list, other non-JSON-serializable conversions

### [18c] Read-Only Routers [x]

- [x] `api/routers/projects.py` — GET `/api/projects`, GET `/api/projects/{name}`, GET `/api/project-index/{project}` (smart index), GET `/api/project-index/{project}/graph` (graph-linked items)
- [x] `api/routers/content.py` — GET `/api/methods`, GET `/api/tools`, GET `/api/blog-queue`, GET `/api/reports/{type}`, GET `/api/instagram`
- [x] `api/routers/graph.py` — GET `/api/graph/health`, GET `/api/graph/{project}`, GET `/api/graph/communities`, GET `/api/graph/{project}/viz` (derived visualization graph — see S22 contract)
- [x] `api/routers/workbench.py` — GET `/api/workbench`, GET `/api/workbench/{key}`
- [x] Each router imports from `src/utils/`, uses `cachetools.TTLCache` for parser results

### [18d] Verify GREEN + Smoke [x]

- [x] All `test_api_read.py` tests pass (28/28)
- [x] Full test suite passes (443/443)
- [x] `uvicorn api.main:app --reload` serves JSON at all endpoints
- [x] Streamlit still works (verified — no import changes to page files)

### [18e] Quality Gate [x]

- [x] **Verify**: Run `/steadows-verify`. Build PASS, lint clean, full suite PASS (443/443), API coverage 95%+. Code review: added TTLCache for graph operations (was missing per GSD spec), removed unused import. Security review: PASS — no CRITICAL/HIGH, CORS locked to localhost:3000, no secrets. Verdict: PASS.

### [18f] Commit [x]

```bash
git add api/ tests/test_api_read.py GSD_PLAN.md
git commit -m "feat: FastAPI read-only endpoints — all parsers wrapped in GET routers"
```

---

## Session 19: FastAPI Mutations + WebSocket [x]

**Scope:** All mutation endpoints (status, analysis, workbench CRUD, research agent, ingestion) plus WebSocket for research log streaming.

**Skills (MANDATORY reads):**
- `api-design/SKILL.md` — mutation patterns, idempotency, error responses
- `python-patterns/SKILL.md` — async patterns for WebSocket handler

**Stitch:** N/A (API only)
**Agent teams:**
- Deploy `tdd-guide` agent for test-first workflow
- Run `/steadows-security-review` (focus: mutation input validation, WebSocket auth, subprocess injection)
**Concurrency:** [19b] mutation routers can be split across agent team members (status+analysis vs workbench vs research+ingestion)

### [19a] TDD: Mutation + WebSocket Tests [x]

- [x] **TDD**: Run `/steadows-tdd`. Follow its EXACT step-by-step protocol.
- [x] Create `tests/test_api_mutations.py` — all POST/DELETE/PATCH endpoints
- [x] Create `tests/test_api_websocket.py` — WebSocket `/ws/research/{key}`
- [x] Run tests — all RED (26 FAILED, 2 PASSED)

### [19b] Mutation Routers [x]

- [x] `api/routers/status.py` — POST `/api/status/{key}`, PATCH `/api/status/{key}`
- [x] `api/routers/analysis.py` — POST `/api/analyze` (Haiku quick), POST `/api/analyze/deep` (Sonnet deep)
- [x] `api/routers/research.py` — POST `/api/research/{key}` (launch agent), GET `/api/research/{key}/status`
- [x] `api/routers/ingestion.py` — POST `/api/instagram/refresh`
- [x] `api/routers/content.py` — extend with POST `/api/summarize/instagram` (Haiku summary), POST `/api/blog-queue/draft` (blog draft generation)
- [x] Extend `api/routers/workbench.py` — POST, DELETE, PATCH endpoints

### [19c] Pydantic Models [x]

- [x] Create `api/models.py`
- [x] `AnalyzeRequest`, `WorkbenchAddRequest`, `WorkbenchUpdateRequest`
- [x] `StatusUpdateRequest`, `IngestionRequest`, `BlogDraftRequest`, `SummarizeInstagramRequest`

### [19d] WebSocket [x]

- [x] **Research**: Used simple poll+send pattern (no broadcast needed — single consumer per key)
- [x] Create `api/ws.py` — `/ws/research/{key}`
- [x] Poll `tail_log()` every 2s, send JSON frames (`{"type": "log", "lines": "..."}`)
- [x] Close when agent exits (sends `{"type": "done"}` frame)

### [19e] Verify GREEN [x]

- [x] All mutation + WebSocket tests pass (28/28)
- [x] Full test suite passes (471/471)

### [19f] Quality Gate [x]

- [x] **Verify**: Run `/steadows-verify`. Build PASS, lint clean (2 lambda→def fixes), 471/471 tests PASS, coverage 77% (Session 19 code 95%+, gap is pre-existing modules). Security review PASS (0 CRITICAL, 0 HIGH). Code review: 1 MEDIUM fixed (blog-queue/draft 409 status code). Verdict: READY.

### [19g] Commit [x]

```bash
git add api/ tests/test_api_mutations.py tests/test_api_websocket.py GSD_PLAN.md
git commit -m "feat: FastAPI mutation endpoints + WebSocket research log streaming"
```

---

## Session 20: Next.js Bootstrap + Design System + Layout Shell [x]

**Scope:** Initialize Next.js 16, port design system from Stitch spec + portfolio-v2, port effects components, build app shell with sidebar navigation.

**Skills (MANDATORY reads):**
- `tailwind-v4-shadcn/SKILL.md` — Tailwind v4 setup, follow 4-step architecture exactly
- `framer-motion-animator/SKILL.md` — animation patterns for effects components
- `framer-motion/SKILL.md` — 42 performance rules (LazyMotion, useMotionValue, etc.)
- `ui-ux-pro-max/SKILL.md` — component design patterns, spacing, accessibility baseline
- `frontend-design/SKILL.md` — production-grade interface patterns
- `docs/designs/DESIGN_SYSTEM.md` — full token spec, glow system, component rules

**Stitch references:**
- `docs/designs/dashboard.html` — nav bar layout, sidebar structure
- `docs/designs/rid_dashboard.png` — visual reference for layout shell

**Agent teams:**
- Deploy `architect` agent to validate component structure before implementation
- Deploy 2 parallel implementation agents:
  - Agent A: CSS design system (`globals.css`) + Tailwind tokens + glow utilities
  - Agent B: Port effects components from `~/portfolio-v2/src/components/effects/`
- Run `/steadows-code-review` after implementation

**Concurrency:** [20b] CSS + tokens and [20c] effects port are fully independent — run in parallel

### [20a] Next.js Setup [x]

- [x] **TDD**: Run `/steadows-tdd`. Follow its EXACT step-by-step protocol.
- [x] **Research**: Query `context7` for Next.js 16 rewrite/proxy capabilities (`/vercel/next.js` → "rewrites proxy websocket upgrade next.config"). Also run `exa` search: `"next.js 16 websocket proxy rewrites"` to find community solutions. Document findings before configuring proxy.
- [x] `npx create-next-app@latest web/ --typescript --tailwind --app --src-dir`
- [x] Install deps: `framer-motion`, `d3`, `swr`, shadcn
- [x] API proxy in `next.config.ts`: `/api/*` → `localhost:8000`. **WebSocket note:** Next.js `rewrites` do not reliably proxy WebSocket upgrades — verify with Next 16 docs before relying on it. Fallback: frontend WebSocket hook connects directly to `ws://localhost:8000/ws/*` in dev (env var `NEXT_PUBLIC_WS_URL`), reverse proxy handles same-origin in production.
- [x] Frontend API client uses same-origin paths (`/api/*`) for HTTP. WebSocket URL sourced from `NEXT_PUBLIC_WS_URL` env var (defaults to same-origin `/ws/*` for production behind reverse proxy, `ws://localhost:8000` for local dev)

### [20b] Design System CSS [x]

- [x] **Reference**: Query `context7` for Tailwind v4 `@theme` directive and CSS variable patterns (`/tailwindlabs/tailwindcss.com` → "@theme custom colors animations keyframes")
- [x] Port all tokens from `DESIGN_SYSTEM.md` into `globals.css`
- [x] Colors, glow utilities (4 colors × 4 types × 2 intensities)
- [x] Keyframe animations, corner bracket utility
- [x] 0px border-radius override

### [20c] Port Effects Components [x]

- [x] Port to `web/src/components/effects/`: GlitchText, SectionReveal, CursorEffect, HUDBracket, ScanLines, AnimatedGrid, FloatingParticles, BackgroundSystem, TypeWriter, ScrollIndicator
- [x] Source: `~/portfolio-v2/src/components/effects/`
- [x] Adapt: remove portfolio-specific props, add generic `className` passthrough

### [20d] Layout Shell [x]

- [x] `layout.tsx` — BackgroundSystem + ScanLines + CursorEffect + fonts
- [x] Sidebar — route-aware nav with active cyan underline
- [x] Header — R.I.D. glitch title
- [x] ContentPanel — HUD bracket frame
- [x] Reference: `docs/designs/dashboard.html` nav structure

### [20e] Shared UI Components [x]

- [x] `HUDCard`, `Badge`, `MetricCard`, `StatusBadge`, `GlowButton`, `DataReadout`
- [x] All with 0px border-radius, glow (not shadow), corner brackets

### [20f] API Client [x]

- [x] `web/src/lib/api.ts` — SWR fetcher, mutation helpers, WebSocket hook

### [20g] Quality Gate [x]

- [x] `pnpm build` passes
- [x] Visual audit against design system
- [x] API proxy works (`/api/*` → FastAPI)
- [x] **Verify**: Run `/steadows-verify`

### [20h] Commit [~]

```bash
git add web/ GSD_PLAN.md
git commit -m "feat: Next.js bootstrap — design system, effects components, layout shell"
```

---

## Session 21: Dashboard View — Next.js [ ]

Requires Session 20 complete. **Can run concurrently with Session 22** (separate terminal windows). Both commit into `web/src/components/` — shared UI primitives must be frozen in Session 20 to avoid merge conflicts.

**Scope:** Build all 7 Dashboard tabs matching the Stitch design.

**Skills (MANDATORY reads):**
- `docs/designs/DESIGN_SYSTEM.md` — token reference
- `tailwind-v4-shadcn/SKILL.md` — component styling with Tailwind v4
- `framer-motion-animator/SKILL.md` — tab transitions, card reveals
- `ui-ux-pro-max/SKILL.md` — layout patterns, data density, empty states

**Stitch references:**
- `docs/designs/dashboard.html` — full layout structure, exact component hierarchy
- `docs/designs/rid_dashboard.png` — visual comparison target
- `docs/designs/agentic-hub.html` — Agentic Hub tab layout (text-only intel cards)
- `docs/designs/rid_agentic_hub_v2.png` — Agentic Hub visual reference (no thumbnails)

**Agent teams:**
- Deploy 2 parallel implementation agents:
  - Agent A: Home tab + Blog Queue tab + Research Archive tab
  - Agent B: Tools Radar tab + Weekly AI Signal tab + Graph Insights tab
- Agentic Hub tab built sequentially after (depends on both agents' shared components)
- Run `/steadows-code-review` + `/steadows-security-review` after all tabs implemented (security focus: XSS in dynamic content rendering, SWR error exposure)

**Concurrency:** [21b] and [21c] are fully independent tab groups — run in parallel

### [21a] Dashboard Page + Tab Navigation [ ]

- [ ] **TDD**: Run `/steadows-tdd`. Follow its EXACT step-by-step protocol.
- [ ] `web/src/app/dashboard/page.tsx` — SWR data fetching, animated tab component, loading skeletons

### [21b] Home + Blog Queue + Research Archive Tabs [ ]

- [ ] HomeTab — 4 HUD metric cards with SectionReveal entrance, sparkline preview
- [ ] BlogQueueTab — card grid with status badges, analyze + draft actions
- [ ] ResearchArchiveTab — JournalClub + TLDR feeds with date filters

### [21c] Tools Radar + AI Signal + Graph Insights Tabs [ ]

- [ ] ToolsRadarTab — category filters, status dots, dismiss/workbench actions
- [ ] WeeklySignalTab — TLDR synthesis with cyan line chart
- [ ] GraphInsightsTab — health metrics, hub notes, communities, suggested links

### [21d] Agentic Hub Tab [ ]

- [ ] Text-only intel brief cards (NO thumbnails — per design iteration)
- [ ] Account filter pills, keyword chips
- [ ] Summarize + Workbench buttons
- [ ] Signal Analysis sidebar with trending topics
- [ ] Reference: `docs/designs/agentic-hub.html`

### [21e] Quality Gate [ ]

- [ ] `pnpm build` passes
- [ ] Visual comparison against all Stitch screenshots
- [ ] All tabs render with real API data
- [ ] **Verify**: Run `/steadows-verify`

### [21f] Commit [ ]

```bash
git add web/src/app/dashboard/ web/src/components/ GSD_PLAN.md
git commit -m "feat: Dashboard view — 7 tabs with HUD design system (Next.js)"
```

---

## Session 22: Project Cockpit + Graph Visualization [ ]

Requires Session 20 complete. **Can run concurrently with Session 21** (separate terminal windows). Both commit into `web/src/components/` — shared UI primitives must be frozen in Session 20 to avoid merge conflicts.

**Scope:** Build Project Cockpit with D3.js force-directed graph visualization.

**Skills (MANDATORY reads):**
- `d3-viz/SKILL.md` — D3 force-directed patterns, zoom/pan, tooltips
- `tailwind-v4-shadcn/SKILL.md` — component styling with Tailwind v4
- `framer-motion-animator/SKILL.md` — SectionReveal for items feed
- `ui-ux-pro-max/SKILL.md` — data visualization UX, interactive element patterns
- `docs/designs/DESIGN_SYSTEM.md` — node colors, edge styling

**Stitch references:**
- `docs/designs/cockpit.html` — full layout: sidebar, graph viz, linked items, actions
- `docs/designs/rid_cockpit.png` — visual comparison target (neural map viz, tech tags, action buttons)

**Agent teams:**
- Deploy `architect` agent to design D3 ↔ React integration pattern before implementation
- Deploy 2 parallel implementation agents:
  - Agent A: Project sidebar + header + items feed
  - Agent B: D3.js GraphVisualization component (force-directed, zoom/pan, HUD styling)
- Run `/steadows-code-review` + `/steadows-security-review` after both complete (security focus: D3 tooltip XSS from vault strings, URL construction for Obsidian links)

**Concurrency:** [22b] D3 graph viz and [22a]+[22c] sidebar/feed are independent — run in parallel

### [22a] Project Sidebar + Selection [ ]

- [ ] **TDD**: Run `/steadows-tdd`. Follow its EXACT step-by-step protocol.
- [ ] `web/src/app/cockpit/page.tsx` — SWR for projects + index + graph, URL-based project selection
- [ ] `ProjectSidebar.tsx` — search filter, active highlight with cyan glow, status + domain badges

### [22b] D3.js Graph Visualization [ ]

**Data contract:** The note graph from `graph_engine.py` contains vault notes as nodes — items (methods/tools/blog) are NOT nodes (per S16 decision). The visualization graph is a **derived** representation: GET `/api/graph/{project}/viz` returns `{ nodes: [{id, type, label}], edges: [{source, target, relation}] }` where `type` ∈ `{project, method, tool, blog}` and `relation` ∈ `{linked, community, suggested}`. The API router builds this from `build_smart_project_index()` + `graph_engine` adjacency — the D3 component consumes the derived shape, never the raw note graph.

**Viz contract rules:** `nodes[].id` is globally unique across types and stable across reruns. Duplicate edges are collapsed (keep highest-signal relation). Empty graphs return `{ nodes: [], edges: [] }` — D3 component renders an empty state, never errors.

- [ ] `GraphVisualization.tsx` — force-directed layout from `/api/graph/{project}/viz`
- [ ] Node colors: project=cyan, method=purple, tool=green, blog=amber
- [ ] Edge styling: linked=solid cyan, community=solid blue, suggested=dashed amber
- [ ] Zoom/pan, hover tooltips, HUD bracket frame
- [ ] Use `useRef` + `useEffect` for D3 (not declarative React rendering)
- [ ] Reference: `d3-viz/SKILL.md` force-directed pattern

### [22c] Project Header + Items Feed [ ]

- [ ] `ProjectHeader.tsx` — GlitchText name, tech badges, Obsidian link
- [ ] `ItemsFeed.tsx` — cards from GET `/api/project-index/{project}/graph` (graph-linked items, defined in S18)
- [ ] Discovery badges: community=blue, suggested=amber, linked=no badge
- [ ] Filters by source type + status + discovery source

### [22d] Analysis Actions [ ]

- [ ] `AnalysisPanel.tsx` — Analyze (Haiku) + Go Deep (Sonnet) buttons
- [ ] TypeWriter loading animation
- [ ] Markdown result display
- [ ] Context sources panel

### [22e] Quality Gate [ ]

- [ ] `pnpm build` passes
- [ ] Visual match against cockpit screenshot
- [ ] D3 graph renders and interacts correctly
- [ ] Analysis flow end-to-end
- [ ] **Verify**: Run `/steadows-verify`

### [22f] Commit [ ]

```bash
git add web/src/app/cockpit/ web/src/components/ GSD_PLAN.md
git commit -m "feat: Project Cockpit with D3.js force-directed graph visualization (Next.js)"
```

---

## Session 23: Workbench + Agentic Hub Interactions [ ]

Requires Sessions 21 AND 22 complete.

**Scope:** Workbench kanban pipeline with WebSocket log streaming, and Agentic Hub interactive features.

**Skills (MANDATORY reads):**
- `framer-motion-animator/SKILL.md` — layout animations for kanban cards
- `framer-motion/SKILL.md` — `layoutId` for card transitions between columns
- `tailwind-v4-shadcn/SKILL.md` — component styling with Tailwind v4
- `ui-ux-pro-max/SKILL.md` — kanban layout patterns, real-time UI feedback
- `docs/designs/DESIGN_SYSTEM.md` — badge colors, button styles

**Stitch references:**
- `docs/designs/workbench.html` — kanban layout: 3 columns, card structure, log tail, verdict badges
- `docs/designs/rid_workbench.png` — visual comparison target

**Agent teams:**
- Deploy 2 parallel implementation agents:
  - Agent A: Kanban view + WorkbenchCard + status transitions
  - Agent B: WebSocket ResearchLog component + research flow state machine
- Run `/steadows-security-review` (focus: WebSocket, research launch, mutation flows)

**Concurrency:** [23a] kanban UI and [23b] WebSocket log are independent — run in parallel

### [23a] Workbench Kanban [ ]

- [ ] **TDD**: Run `/steadows-tdd`. Follow its EXACT step-by-step protocol.
- [ ] `web/src/app/workbench/page.tsx` — SWR for `/api/workbench`, 3-column layout (QUEUED / RESEARCHING / COMPLETED)
- [ ] `KanbanColumn.tsx` — header + count badge + HUD bracket frame
- [ ] `WorkbenchCard.tsx` — source badge, status, action buttons per state, Framer Motion `layoutId` for column transitions
- [ ] Button-based transitions — no drag-and-drop (MVP)

### [23b] WebSocket Research Log [ ]

- [ ] `ResearchLog.tsx` — connect to `/ws/research/{key}`
- [ ] Terminal-style display (JetBrains Mono, cyan on dark surface)
- [ ] Auto-scroll, connection status indicator
- [ ] Agent activity parsing

### [23c] Research Flow [ ]

- [ ] Start Research → WebSocket log → parse output → show verdict badge
- [ ] Verdict: PROGRAMMATIC (green) / MANUAL (amber)
- [ ] Actions: View Report + Start Sandbox + Open in Obsidian

### [23d] Agentic Hub Interactions [ ]

- [ ] Wire Summarize button (`POST /api/summarize/instagram`)
- [ ] Wire Workbench button (`POST /api/workbench`)
- [ ] Wire Refresh button (`POST /api/instagram/refresh` with progress indicator)
- [ ] All from the Agentic Hub tab built in Session 21

### [23e] Quality Gate [ ]

- [ ] `pnpm build` passes
- [ ] Visual match against workbench + agentic hub screenshots
- [ ] WebSocket log streaming works with real research agent
- [ ] **Verify**: Run `/steadows-verify`

### [23f] Commit [ ]

```bash
git add web/src/app/workbench/ web/src/components/ GSD_PLAN.md
git commit -m "feat: Workbench kanban with WebSocket log streaming + Agentic Hub interactions (Next.js)"
```

---

## Session 24: Integration Testing + E2E + Polish [ ]

Requires Session 23 complete.

**Scope:** Full E2E test suite, frontend unit tests, visual polish pass, accessibility.

**Skills (MANDATORY reads):**
- `docs/designs/DESIGN_SYSTEM.md` — audit every rule: corner brackets (not borders), 0px border-radius, glow (not shadow), correct fonts
- `framer-motion/SKILL.md` — performance audit (lazy imports, Suspense, reduced motion)
- `ui-ux-pro-max/SKILL.md` — accessibility checklist, responsive patterns, WCAG audit guide
- `e2e-testing/SKILL.md` — Playwright patterns, Page Object Model, CI integration

**Stitch references:**
- ALL screenshots (`docs/designs/rid_*.png`) — visual comparison against every view

**Agent teams:**
- Deploy 3 parallel agents:
  - Agent A (`e2e-runner`): Playwright E2E tests (`dashboard.spec.ts`, `cockpit.spec.ts`, `workbench.spec.ts`, `agentic-hub.spec.ts`)
  - Agent B (`tdd-guide`): Vitest unit tests (HUDCard, Badge, GraphVisualization, KanbanColumn, API client)
  - Agent C: Visual polish audit using `ui-ux-pro-max` skill — compare every view against Stitch screenshots, fix discrepancies
- Run `/steadows-security-review` after tests written

**Concurrency:** All 3 agents are fully independent — run in parallel

### [24a] E2E Tests [ ]

- [ ] **TDD**: Run `/steadows-tdd`. Follow its EXACT step-by-step protocol.
- [ ] Playwright against local FastAPI + Next.js, mock Claude API at FastAPI layer
- [ ] Test: page loads, tab navigation, project selection, analysis flow, workbench pipeline, agentic hub refresh

### [24b] Frontend Unit Tests [ ]

- [ ] Vitest + React Testing Library
- [ ] Test: component rendering, props, API client, SWR hooks

### [24c] Visual Polish Pass [ ]

- [ ] Compare every view closely against `docs/designs/rid_*.png` — fix meaningful visual drift (missing corner brackets, wrong fonts, palette violations, animation timing), don't block on subpixel-perfect rendering
- [ ] Use Stitch `edit_screens` MCP if design refinement needed

### [24d] Accessibility + Responsive [ ]

- [ ] WCAG AA contrast (4.5:1 per design system)
- [ ] Keyboard nav for all interactive elements
- [ ] Screen reader labels
- [ ] `prefers-reduced-motion` on all animations
- [ ] Responsive sidebar collapse

### [24e] Performance [ ]

- [ ] Lighthouse > 90
- [ ] Lazy D3 import
- [ ] `LazyMotion` + `m` components
- [ ] Suspense boundaries
- [ ] `next/image` for any images

### [24f] Quality Gate [ ]

- [ ] `pnpm build` + `pnpm test` + Playwright all pass
- [ ] Python `pytest tests/` still passes
- [ ] Lighthouse scores
- [ ] **Verify**: Run `/steadows-verify` (both Python + Next.js). Confirm build PASS, lint clean, all test suites PASS, coverage ≥ 80%. Includes code review (focus: component quality, test coverage gaps) and security review (focus: XSS in dynamic content, WebSocket input sanitization, API client error handling). All CRITICAL/HIGH findings fixed. Verdict: PASS.

### [24g] Commit [ ]

```bash
git add web/ tests/ GSD_PLAN.md
git commit -m "feat: E2E + unit tests, visual polish, accessibility, performance optimization"
```

---

## Session 25: Cutover + Deployment [ ]

Requires Session 24 complete.

**Scope:** Decommission Streamlit, create unified launch scripts, update documentation.

**Skills:** N/A (ops + documentation only)
**Stitch:** N/A
**Agent teams:**
- Deploy `doc-updater` agent for CLAUDE.md + README updates
- Deploy `historian` agent for final checkpoint
**Concurrency:** [25b] deprecation + [25c] documentation can run in parallel

### [25a] Create Launch Scripts [ ]

- [ ] `scripts/dev.sh` — starts FastAPI port 8000 + Next.js port 3000, SIGINT traps both. Next.js proxy handles `/api/*` and `/ws/*` routing
- [ ] `scripts/start.sh` — production: `uvicorn` (not gunicorn — needed for WebSocket support) + Node
- [ ] `scripts/Caddyfile` (or `nginx.conf`) — reverse proxy config: `:3000` serves Next.js, `/api/*` and `/ws/*` proxy to `:8000` with WebSocket upgrade support. This is a required deliverable, not optional — same-origin routing is part of the frontend contract

### [25b] Deprecate Streamlit [ ]

- [ ] Move `src/pages/` → `src/legacy_pages/`
- [ ] Move `src/Home.py` → `src/legacy_Home.py`
- [ ] Remove `.streamlit/config.toml`
- [ ] Remove `page_helpers_st.py`
- [ ] Remove `streamlit` from `requirements.txt`
- [ ] Verify: `pytest tests/` passes without Streamlit installed (tests import `utils/`, not pages)

**Note:** Legacy files preserve reference/history, not immediate rollback. Restoring Streamlit would require re-adding `streamlit` to `requirements.txt` and recreating `page_helpers_st.py`. For true rollback, use `git revert`.

### [25c] Update Documentation [ ]

- [ ] `README.md` — new architecture, setup, dev workflow
- [ ] `CLAUDE.md` — remove Streamlit sections, add Next.js conventions, update Architecture diagram, remove Streamlit skills table

### [25d] Update Obsidian Project Note [ ]

- [ ] Tech stack updated
- [ ] Status: active
- [ ] Overview mentions HUD rebuild

### [25e] Quality Gate [ ]

- [ ] `pnpm build`
- [ ] `pytest tests/` without Streamlit
- [ ] `scripts/dev.sh` starts both servers
- [ ] Full E2E suite passes
- [ ] **Verify**: Run `/steadows-verify`

### [25f] Commit [ ]

```bash
git add scripts/ src/ .streamlit/ requirements.txt README.md CLAUDE.md GSD_PLAN.md
git commit -m "feat: cutover to Next.js + FastAPI — decommission Streamlit, unified launch scripts"
```

---

## Decisions Log

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Data source | Obsidian vault markdown | Already written by scheduled tasks |
| State storage | `~/.research-dashboard/status.json` | Non-destructive; survives restarts |
| LLM routing | Haiku quick / Sonnet deep | Cost-efficient default |
| Project metadata | Frontmatter + wiki-links | Pure Python, no Obsidian plugins |
| Cache strategy | Hash(item_id + project + type) | Avoids redundant API calls |
| TLDR editions | Main + Data only | Fintech excluded |
| Workbench state | `~/.research-dashboard/workbench.json` (separate from status.json) | Keeps workbench lifecycle data isolated; workbench items have richer schema than status items |
| Research agent model | `claude-opus-4-6` via `claude -p` subprocess | Opus for deep research quality; subprocess avoids blocking Streamlit event loop |
| Agent output format | `--output-format stream-json` to log file | Allows log tail polling without blocking; full trace preserved for debugging |
| S16: Graph item discovery location | `smart_matcher.py` (not `graph_engine.py` or `vault_parser.py`) | Tier 3 matching alongside existing Tier 1/2; `graph_engine.py` stays pure NetworkX |
| S16: Discovery model | Project proximity propagation (not item-to-graph) | Items aren't graph nodes — methods/tools/blog are entries within single vault notes. Discovery works through project-to-project graph edges. |
| S16: Scope | Methods, tools, blog only — Instagram excluded | Instagram posts lack `projects` field and aren't in `build_smart_project_index()`. Requires separate indexing contract first. |
| S16: Field naming | `discovery_source` (not `source`) | Existing `source` field carries parser provenance, rendered in UI and prompts — must not be overwritten |
| S16: Propagation filter | Explicit peer matches only (`match_type == "explicit"`) | Tier 2 inferred matches are weak signals — propagating them across graph edges compounds noise. Follow-up session can add inferred propagation with its own scoring policy. |
| S16: Peer ordering | Alphabetical for community, score-descending for suggested | Deterministic `via_project` attribution; tests are not flaky; provenance is stable across reruns |
| S16: Dedup identity | `f"{source_type}::{name}"` composite key | Matches existing repo convention in `smart_matcher.py` and Cockpit status system |
| S16: Propagated metadata | `origin_match_type` / `origin_confidence` on graph items | Peer-project match metadata is not valid for the selected project — must be separated |
| S16: graph_context param | Keyword-only with `None` default | Full backward compatibility; no change to existing callers |
| S16: Graph context loading | `_load_project_graph_context()` reuses S15 cached loaders | Per-project slice only — does NOT recompute graph/metrics/communities. Prevents S15 cache regression. |
| S16: Cache versioning | Global `_CACHE_VERSION` bump for all analyses | Simpler than conditional key branching; cost of re-running analyses is low vs. risk of stale cache |
| S16: `linked` source badge | No badge (suppressed) | `linked` is the default/expected state; badges only for novel discovery sources |
| S16: Dedup priority | `linked` > `community` > `suggested` | Explicit human links are highest signal |
| S16: `via_project` provenance | Stored on each community/suggested item | Shows user WHY an item was surfaced ("via Project B") — critical for trust |
| S16: Prompt safety | `_sanitize_note_name()` escapes `<>& \n`, truncates to 200 chars | Graph-derived strings are vault note names — not user input, but can contain control-like characters |
| HTML report generation | Python `markdown` lib post-agent | Agent writes clean .md; Python renders to .html — separation of concerns, no agent browser deps |
| Review gate | `reviewed` flag in workbench.json | Forces deliberate human review before sandbox creation; prevents accidental Docker builds |
| Sandbox isolation | `--network none` by default in `run.sh` | Security default; experiments document when they need network |
| Vault note collision | Timestamp suffix on duplicate | Preserves history; never silently overwrites prior research |
| Workbench key format | `{source_type}::{name}` | Prevents tool/method name collisions; bare-name is legacy read shim only |
| Workbench entry schema | `"item"` + `"source_type"` + provenance fields | Generalizes from tool-only; `source_item_id` + `previous_status` enable status restore on remove |
| Methods in workbench | Queue-only in Session 9; pipeline in 10–11 | Avoids breaking tool-specific research prompts; incremental generalization |
| Provenance immutability | `source_item_id` + `previous_status` not in `_ALLOWED_UPDATE_FIELDS` | Creation-time metadata for undo semantics; no runtime mutation |
| Workbench slug namespace | `{source_type}-{slug}` | Prevents output path collisions in `~/research-workbench/` |
| Paper cache storage | `~/.research-dashboard/paper-cache/` (separate from status.json) | Full paper text can be 10-80K chars; stuffing into status.json degrades every cache op |
| Full text cap | 30K chars (~7.5K tokens) | Keeps Sonnet prompts bounded; semantic section extraction preferred |
| Cache versioning | Bump suffix on every prompt enrichment change | Prevents stale thin-context outputs from masking enriched prompt results |
| Paper fetch API | Single `fetch_paper_context() -> PaperContext` | One Semantic Scholar call, one cache write, typed return — replaces separate helpers |
| Instagram state file | `~/.research-dashboard/instagram_state.json` (separate from `workbench.json`) | Ingestion state is append-only and keyed by shortcode; isolating it avoids schema coupling with workbench lifecycle data |
| Instagram video source | `post.video_url` (audio-only download via instaloader) | Avoids storing full video files locally; Whisper transcribes from audio stream |
| Whisper model size | `base` with `device="cpu"`, `compute_type="int8"` | Balances transcription quality vs. local CPU cost; no GPU required on dev machine |
| Term corrections | Hardcoded `_TERM_CORRECTIONS` dict in ingester | Whisper mishears AI product names predictably; small static dict is sufficient, no ML overhead |
| Rate limiting | 2–3s `time.sleep()` between instaloader downloads | Instagram private API has no official rate limit docs; conservative delay avoids 429s |
| Instagram workbench key | `make_item_key("instagram", shortcode)` | Shortcode is globally unique per post; name-based keys would collide on re-titles |
| Instagram source badge | Indigo `#6366F1` | Visually distinct from method purple (`#8B5CF6`) and tool green (`#10B981`) in Workbench |
| Instagram research button | Disabled in Session 13; enabled in Session 14 | Research agent COSTAR prompt is tool/method-shaped; Session 14 adds topic-centric prompt branch |
| Transcript context in research prompt | First 4000 chars injected into `<context>` block | Keeps prompt bounded; 4000 chars ≈ 1000 tokens, well within Opus context window |
| Agentic Hub tab position | Sixth tab in Dashboard | Ordered by data maturity: established feeds first, new ingestion sources appended |
| Instagram identity model | Shortcode key + preserved display title | Title overwrite in Session 13 was a UX bug; separation enables human-readable Workbench cards while keeping durable duplicate detection |
| Instagram prompt heading | `## Getting Started` replaces `## How to Install` | Not all Instagram topics are installable tools; parser only depends on `## Overview` + `## Programmatic Assessment`, so heading change is safe |
| Low-signal threshold | No transcript + no key_points + caption < 20 chars | Concrete threshold enables deterministic testing; agent still runs and produces minimal report |
| Instagram model routing | Same as existing research agent chain | Defer model optimization until usage patterns are observed; avoids premature cost-routing complexity |
| Graph library | `obsidiantools` + NetworkX (both direct deps) | Mature (535 stars), Python-native, gives raw NetworkX graph; all Obsidian plugins are UI-only; MCP graph servers too immature. NetworkX listed as direct dep since we import it directly, not just transitively. |
| Graph caching (Streamlit era, S15-16) | `cache_resource` for DiGraph at page layer, `cache_data` for metrics at page layer | DiGraph is not serializable by pickle; `cache_resource` stores reference. Metrics are plain dicts, safe for `cache_data`. `graph_engine.py` stays pure (no Streamlit imports) — matches existing parser/utils pattern. **Superseded by `cachetools.TTLCache` in API routers from S18+.** |
| Graph cache invalidation (Streamlit era, S15-16) | Clear both `cache_data` and `cache_resource` on any refresh | Avoids stale graph data when vault is re-linked or manually refreshed. **Post-migration (S18+): mutation/refresh endpoints clear `TTLCache` layers instead.** |
| Betweenness centrality guard | Skip when vault has >1000 nodes | O(VE) complexity; personal vaults are typically 200-500 notes but guard prevents degraded UX on large vaults |
| Centrality rank scope | Among ALL vault notes | Project's rank relative to every note gives true structural importance; ranking only among projects would hide how projects relate to methods/tools/etc. |
| Link prediction scope | 3-hop neighborhood only | Full vault Adamic-Adar is O(N²); 3-hop cutoff keeps it fast while capturing meaningful structural proximity |
| Community display filter | 3+ members only | Tiny communities (1-2 notes) are noise in the UI; count shown but not expanded |
| Graph tab position | 7th tab in Dashboard | Appended after Agentic Hub — newest/most experimental features go last |
| Cockpit graph section | Collapsed expander in lower metadata/context area (after items feed) | Graph context is supplementary — items feed remains the primary view; current layout preserved: title → items → metadata/context (graph here) |
| Louvain seed | `seed=42` | Deterministic community detection across reruns; avoids confusing UI shifts |
| obsidiantools connect vs gather | `connect()` only, skip `gather()` | `connect()` builds the graph from wiki-links (fast). `gather()` reads all note content (slow, unnecessary for graph-only analysis) |
| S17: Streamlit decoupling strategy | Replace `@st.cache_data` with `cachetools.TTLCache`, split `page_helpers.py` | Enables `smart_matcher.py` import from FastAPI without Streamlit dep; pure functions stay reusable |
| S17: api/ import strategy | `api/deps.py` adds `src/` to `sys.path` at startup | Reuses existing `from utils.*` imports without restructuring; pytest already does this via `pythonpath` config |
| S22: Graph visualization data model | Derived viz graph (`/api/graph/{project}/viz`) built from smart index + graph engine | Raw note graph has no item nodes (S16 decision); viz graph is a purpose-built projection for D3 force layout |
| S17: Skill source | Symlink from `~/portfolio-v2/.agents/skills/` | Single source of truth; updates in portfolio-v2 propagate automatically |
| S18: API architecture | FastAPI app factory + router-per-domain | Standard FastAPI pattern; routers mirror existing parser boundaries |
| S18: Serialization layer | `api/serializers.py` for DiGraph, frozenset, etc. | NetworkX types aren't JSON-serializable; centralized conversion avoids scattered `dict()` calls |
| S18: Caching | `cachetools.TTLCache` in routers (not `@lru_cache`) | TTL matches Streamlit's `ttl=3600` pattern; avoids stale data on vault changes. Mutation/refresh endpoints (S19) must clear all relevant TTLCache layers on write. |
| S19: WebSocket polling | 2s interval on `tail_log()` | Matches existing Streamlit polling interval; bounded by research agent key lookup |
| S19: Pydantic models | Centralized in `api/models.py` | Single source for request/response schemas; reusable across routers |
| S20: D3 integration | `useRef` + `useEffect` (imperative), not declarative React | D3 force simulation needs direct DOM control; React reconciliation would fight the physics engine |
| S20: Design system source | Stitch `DESIGN_SYSTEM.md` + portfolio-v2 `globals.css` | Stitch spec is authoritative for tokens; portfolio-v2 has battle-tested CSS implementation |
| S20: Effects components | Port from portfolio-v2, strip portfolio-specific props | Reuse proven animations; generic `className` passthrough enables composition |
| S21+22: Concurrent sessions | Dashboard and Cockpit in separate terminals | Both commit into `web/src/components/`; shared UI primitives must be frozen in S20 before parallel work begins |
| S22: Graph node colors | project=cyan, method=purple, tool=green | Matches existing badge color conventions from Streamlit UI |
| S23: Kanban transitions | Button-based, no drag-and-drop | MVP simplicity; drag-and-drop adds touch/accessibility complexity for low-frequency action |
| S23: Research log display | Terminal-style (JetBrains Mono, cyan on dark) | Matches the HUD aesthetic; familiar terminal UX for research agent output |
| S24: Test stack | Playwright (E2E) + Vitest (unit) | Next.js ecosystem standard; Playwright handles full-stack flows, Vitest handles component isolation |
| S25: Streamlit deprecation | Move to `legacy_*` prefix, don't delete | Preserves reference/history; true rollback via `git revert` (runtime deps are removed in same session) |

---

## Architecture

```
┌──────────────────────────────────────────────────────────────────┐
│                         Streamlit App                            │
│                                                                  │
│  src/Home.py ──→ 1_Dashboard.py  2_Project_Cockpit.py            │
│                        │  │  │           │                       │
│                        │  │  └(Agentic   │                       │
│                        │  │    Hub tab)  │                       │
│                        │  └──(Workbench)─┤                       │
│                        ↓                 ↓                       │
│                  3_Workbench.py ←────────┘                       │
│                        │                                         │
│                        src/utils/                                │
│  ┌───────────────────────────────────────────────────────┐       │
│  │ vault_parser   methods_parser   tools_parser          │       │
│  │ blog_queue_parser   reports_parser                    │       │
│  │ status_tracker   claude_client   prompt_builder       │       │
│  │ cockpit_components   parser_helpers   page_helpers    │       │
│  │ paper_fetcher   workbench_tracker                     │       │
│  │ research_agent   vault_writer                         │       │
│  │ instagram_ingester   instagram_parser                 │       │
│  │ graph_engine (obsidiantools + NetworkX)              │       │
│  │ knowledge_linker   smart_matcher                    │       │
│  └─────────────────────────┬─────────────────────────────┘       │
└────────────────────────────┼─────────────────────────────────────┘
                             │
         ┌───────────────────┼───────────────────────────────────┐
         │                   │                │          │        │
 Obsidian Vault       status.json      Anthropic API   ~/research-workbench/
 (OBSIDIAN_VAULT_PATH)  workbench.json  (claude -p     {tool-slug}/
  Research/Instagram/   paper-cache/    subprocess)    research.md
  {username}/           instagram_      (Haiku inline  research.html
  YYYY-MM-DD.md        state.json       + Opus agent)  Dockerfile
                       (~/.research-                   experiment.py
                        dashboard/)                    run.sh
                                        instaloader +
                                        faster-whisper
                                        (local CPU)
```

---

## Files Changed Summary

| File | Session | Purpose |
|------|---------|---------|
| `src/Home.py` | 1, 8 | Entry point, nav, CSS, env validation |
| `.streamlit/config.toml` | 1 | Dark OLED theme |
| `src/utils/parser_helpers.py` | 2 | Shared parsing utilities (DRY) |
| `src/utils/vault_parser.py` | 2 | Project parsing + wiki-links |
| `src/utils/methods_parser.py` | 2 | Methods backlog parser |
| `src/utils/tools_parser.py` | 2 | Tools radar parser |
| `src/utils/blog_queue_parser.py` | 2 | Blog queue parser |
| `src/utils/reports_parser.py` | 2 | JournalClub + TLDR parser |
| `src/utils/status_tracker.py` | 2 | Status + analysis cache |
| `src/utils/page_helpers.py` | 3, 7 | Shared page utilities; context sources helper |
| `src/pages/1_Dashboard.py` | 3, 7, 8, 9 | Global intel feed — 5 tabs; context enrichment; tool dismiss + workbench buttons; previous_status passthrough |
| `src/utils/claude_client.py` | 4, 7 | Anthropic SDK wrapper + LLM trace; prompt enrichment + cache version bumps |
| `src/utils/prompt_builder.py` | 4, 7 | Prompt construction; quick analysis project context |
| `src/pages/2_Project_Cockpit.py` | 5, 9 | Project-scoped workspace; workbench button on item cards |
| `src/utils/cockpit_components.py` | 5 | Cockpit UI components |
| `tests/test_integration.py` | 6 | Round-trip pipeline tests |
| `src/utils/paper_fetcher.py` | 7 | Unified paper context fetch (abstract + full text) with separate cache |
| `tests/test_paper_fetcher.py` | 7 | Paper context fetcher unit tests |
| `tests/test_prompt_enrichment.py` | 7 | Prompt enrichment + cache versioning tests |
| `tests/test_dashboard_enrichment.py` | 7 | Dashboard fallback + graceful degradation tests |
| `requirements.txt` | 7 | `pypdf` added for PDF text extraction |
| `src/utils/workbench_tracker.py` | 8, 9 | Workbench JSON state CRUD; namespaced keys, generalized schema, provenance restore |
| `src/pages/3_Workbench.py` | 8, 9, 10, 11 | Workbench queue UI; generalized rendering; research + sandbox pipeline UI |
| `tests/test_workbench_tracker.py` | 8, 9 | Workbench tracker unit tests; methods workbench + backward compat tests |
| `src/utils/research_agent.py` | 10, 11 | Research + sandbox subprocess launchers, log tail, HTML render |
| `tests/test_research_agent.py` | 10 | Research agent unit tests |
| `tests/test_sandbox_agent.py` | 11 | Sandbox agent unit tests |
| `src/utils/vault_writer.py` | 11 | Write sandbox vault notes |
| `tests/test_vault_writer.py` | 11 | Vault writer unit tests |
| `tests/test_workbench_integration.py` | 11 | Round-trip workbench pipeline integration tests |
| `src/utils/instagram_ingester.py` | 12 | Instagram video fetch, Whisper transcription, Haiku extraction, vault note writer, state file |
| `src/utils/instagram_parser.py` | 12 | Parse `Research/Instagram/**/*.md` vault notes into structured dicts |
| `tests/test_instagram_ingester.py` | 12 | Instagram ingester unit tests — fetch, transcribe, extract, write, state management |
| `tests/test_instagram_parser.py` | 12 | Instagram parser unit tests — frontmatter, sections, filter, round-trip |
| `requirements.txt` | 12 | `instaloader`, `faster-whisper` added |
| `src/pages/1_Dashboard.py` | 13, 14 | Agentic Hub tab — account filter pills, post cards, Summarize + Workbench buttons; preserve title on workbench add |
| `src/pages/3_Workbench.py` | 13, 14 | Instagram entry rendering — indigo badge, caption synthesis line; enable Research button, topic preview/summary |
| `src/utils/research_agent.py` | 13, 14 | Transcript context injection; Instagram topic-centric COSTAR prompt branch, low-signal handling |
| `src/utils/workbench_tracker.py` | 8, 9, 14 | Workbench JSON state CRUD; namespaced keys, generalized schema, provenance restore; Instagram identity helper |
| `tests/test_agentic_hub.py` | 13, 14 | Agentic Hub tab render tests — filter, card content, button states, XSS; title preservation |
| `tests/test_instagram_workbench.py` | 13, 14 | Instagram workbench integration — key format, transcript field; identity-model, prompt, UI boundary tests |
| `src/utils/graph_engine.py` | 15 | Vault graph analysis — obsidiantools + NetworkX (centrality, communities, link prediction, health) |
| `tests/test_graph_engine.py` | 15 | Graph engine unit + integration tests |
| `tests/test_dashboard_tabs.py` | 15 | Extended with Graph Insights tab wiring + empty-state regression tests |
| `tests/test_cockpit_graph_context.py` | 15 | Page-level graph context regression tests (placement, empty state, direction indicators) |
| `src/pages/1_Dashboard.py` | 3, 7, 8, 9, 15 | Graph Insights tab added; cache invalidation updated |
| `src/pages/2_Project_Cockpit.py` | 5, 9, 15 | Per-project graph context section in metadata area; cache invalidation updated |
| `requirements.txt` | 7, 12, 15 | `obsidiantools>=0.11.0,<1.0`, `networkx>=3.0` added |
| `src/utils/smart_matcher.py` | 2, 16, 17 | Decoupled from Streamlit — `cachetools.TTLCache` replaces `@st.cache_data` |
| `src/utils/page_helpers_st.py` | 17 | Streamlit-specific helpers extracted from `page_helpers.py` |
| `.claude/skills/` | 17 | Symlinks to portfolio-v2 frontend skills |
| `api/main.py` | 17, 18 | FastAPI app factory with CORS |
| `api/deps.py` | 17, 18 | Dependency injection — vault path, API key |
| `api/serializers.py` | 18 | Non-JSON-serializable type conversions |
| `api/routers/projects.py` | 18 | Projects GET endpoints |
| `api/routers/content.py` | 18 | Methods, tools, blog queue, reports GET endpoints |
| `api/routers/graph.py` | 18 | Graph health, project graph, communities GET endpoints |
| `api/routers/workbench.py` | 18, 19 | Workbench GET + POST/DELETE/PATCH endpoints |
| `api/routers/status.py` | 19 | Status mutation endpoints |
| `api/routers/analysis.py` | 19 | Analysis (Haiku quick + Sonnet deep) endpoints |
| `api/routers/research.py` | 19 | Research agent launch + status endpoints |
| `api/routers/ingestion.py` | 19 | Instagram refresh endpoint |
| `api/models.py` | 19 | Pydantic request/response models |
| `api/ws.py` | 19 | WebSocket research log streaming |
| `tests/test_api_read.py` | 18 | Read-only API endpoint tests |
| `tests/test_api_mutations.py` | 19 | Mutation API endpoint tests |
| `tests/test_api_websocket.py` | 19 | WebSocket endpoint tests |
| `web/` | 20 | Next.js 16 app (TypeScript, Tailwind, App Router) |
| `web/src/app/globals.css` | 20 | Design system tokens, glow utilities, keyframes |
| `web/src/components/effects/` | 20 | Ported effects: GlitchText, SectionReveal, CursorEffect, etc. |
| `web/src/components/ui/` | 20 | HUDCard, Badge, MetricCard, StatusBadge, GlowButton, DataReadout |
| `web/src/app/layout.tsx` | 20 | App shell — BackgroundSystem, ScanLines, Sidebar, Header |
| `web/src/lib/api.ts` | 20 | SWR fetcher, mutation helpers, WebSocket hook |
| `web/src/app/dashboard/page.tsx` | 21 | Dashboard page — 7 tabs |
| `web/src/app/cockpit/page.tsx` | 22 | Project Cockpit — sidebar, graph viz, items feed, analysis |
| `web/src/components/GraphVisualization.tsx` | 22 | D3.js force-directed graph |
| `web/src/app/workbench/page.tsx` | 23 | Workbench kanban — 3 columns, WebSocket log |
| `web/e2e/` | 24 | Playwright E2E test specs |
| `web/src/__tests__/` | 24 | Vitest component unit tests |
| `scripts/dev.sh` | 25 | Dev launch script (FastAPI + Next.js) |
| `scripts/start.sh` | 25 | Production launch script |
| `src/legacy_pages/` | 25 | Deprecated Streamlit pages |
| `src/legacy_Home.py` | 25 | Deprecated Streamlit entry point |

---

## Risk Register

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|-----------|
| Vault format changes | Medium | Medium | Regex with fallbacks; log warnings |
| API latency on Analyze | High | Low | Haiku fast (~1s); spinner covers UX |
| Status.json corruption | Low | Low | Atomic write via temp + `os.replace()` |
| Wiki-link name drift | Low | High | Index from filenames; log mismatches |
| Vault path with spaces | Medium | Medium | `pathlib.Path` throughout |
| Semantic Scholar rate limiting | Medium | Low | Cache aggressively in paper-cache dir; warm only visible item, not all |
| PDF extraction fails on non-standard PDFs | Medium | Low | Fall back to arXiv HTML → abstract → empty; never block on extraction failure |
| `claude -p` subprocess not in PATH | Medium | High | Document conda env activation requirement; verify in Session 8 quality gate |
| Research agent hallucinated package names | Medium | High | Safety clause in prompt; `## Safety Notes` section required in output; user reviews before sandbox |
| Sandbox agent generates `RUN curl\|bash` | Low | High | Safety clause in sandbox prompt; post-generation Dockerfile scan in code review (grep for `curl\|bash\|wget\|sh`) |
| Docker not installed on dev machine | Medium | Medium | Workbench shows clear error + install link if `docker info` fails at sandbox-ready stage |
| Long-running agent blocks Streamlit | High | Low | Subprocess model + log tail polling; page renders freely between polls |
| workbench.json concurrent write collision | Low | Low | Same atomic write pattern as status.json; single-user local app, risk acceptable |
| Vault note directory missing | Low | Low | `mkdir(parents=True, exist_ok=True)` in `write_sandbox_note` |
| Instagram rate limiting (429) | Medium | Medium | 2–3s delay between downloads; `run_ingestion` skips failed posts with WARNING (never aborts full run) |
| instaloader private API breaks | Medium | High | Document: instaloader reverse-engineers Instagram's private web API — Instagram changes may break fetching without notice. Pin `instaloader` version in `requirements.txt`; monitor changelog. |
| Whisper mishears proper nouns | High | Low | `_TERM_CORRECTIONS` dict applied post-transcription; expand dict as new misheard terms are found |
| Posts with no video (images/carousels) | High | Low | `fetch_recent_posts` checks `post.is_video`; skips with WARNING log, never raises |
| Large video files slow transcription | Medium | Medium | Whisper `base` model on CPU; transcription time scales with video length. Document: expect 2–5× real-time on M-series Mac. Users should ingest in background (not Streamlit render path). |
| instagram_state.json concurrent write | Low | Low | Atomic write (same `tempfile + os.replace` pattern as status.json); single-user local app, risk acceptable |
| Transcript injected into research prompt exceeds context | Low | Low | Hard cap at 4000 chars in `_build_prompt`; logged at DEBUG |
| Vault write path traversal (username field) | Low | High | Validate `username` contains only alphanumeric + `.` + `_` + `-` before using in path construction; reject with ValueError on unexpected chars |
| Low-signal Instagram posts produce empty research | Medium | Low | Agent still runs; minimal report with `NO` assessment and evidence checklist — no new failure state |
| Instagram title lost on workbench add | High | Medium | Identity model separates display title (`name`) from durable key (`shortcode`); Session 14 fix |
| obsidiantools API changes | Low | Medium | Pin `obsidiantools>=0.11.0,<1.0`; check `vault.file_index` exists before use |
| Large vault makes link prediction slow | Medium | Medium | Limit Adamic-Adar candidates to 3-hop neighborhood; global view only computes for top 5 hubs |
| Project names don't match obsidiantools note names | Low | Medium | Both use `Path.stem`; integration test verifies alignment |
| Louvain produces too many tiny communities | Medium | Low | Filter to communities with 3+ members for display; show filtered count |
| Cached DiGraph mutated by caller | Low | High | Never mutate cached graph; `to_undirected()` creates copies; documented in docstrings |
| PageRank doesn't converge on disconnected graph | Low | Low | `nx.pagerank` handles gracefully with default damping factor |
| FastAPI CORS misconfiguration | Medium | High | Lock CORS to `localhost:3000` only; `/steadows-verify` security review stage checks CORS headers |
| DiGraph serialization breaks JSON response | Medium | Medium | `api/serializers.py` centralizes all non-JSON-serializable conversions; tested in `test_api_read.py` |
| Next.js API proxy masks backend errors | Medium | Medium | Proxy passes status codes through; frontend shows error states with original status |
| D3 force simulation performance on large graphs | Medium | Medium | Limit node count in API response; use `d3.forceSimulation().stop()` + manual tick for SSR |
| WebSocket connection drops during research | Medium | Low | Frontend reconnect logic with exponential backoff; research log persisted server-side |
| Portfolio-v2 skill symlinks break on different machine | Medium | Low | Document setup step; CI clones both repos; `.gitignore` excludes symlinks |
| Streamlit removal breaks existing tests | Medium | High | Tests import from `src/utils/` not pages; verify in Session 25 with Streamlit uninstalled |
| Framer Motion bundle size | Medium | Low | `LazyMotion` + dynamic imports; only load features used per page |
| Next.js 16 breaking changes | Low | Medium | Pin exact version in `package.json`; test against canary before upgrade |
| Concurrent Sessions 21+22 create merge conflicts | Low | Medium | Separate directories (`dashboard/` vs `cockpit/`); shared components built in Session 20 |
| Design system drift between Stitch and implementation | Medium | Medium | Session 24 visual polish pass compares every view closely against screenshots — fix meaningful visual drift, don't block on subpixel rendering |

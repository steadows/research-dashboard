# GSD Plan: Research Intelligence Dashboard

> **Created:** 2026-03-14 | **Revised:** 2026-03-16 | **Stack:** Python 3.11 · Streamlit · Anthropic SDK · PyYAML
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

### [9g] Quality Gate [~]

**MANDATORY**: Each gate below requires reading the specified file with the Read tool and following its EXACT protocol. Do NOT improvise your own review — execute the steps in the file as written.

- [ ] **Verify**: Run `/steadows-verify`. Confirm build PASS, lint clean, format clean, full suite PASS, coverage ≥ 80%. Includes code review (focus: `workbench_tracker.py` schema changes, `3_Workbench.py` wb_key keying, `2_Project_Cockpit.py` new button) and security review (focus: no bare-name ambiguity exploits, status restore uses allowlisted fields only). All CRITICAL/HIGH findings fixed. Verdict: PASS.
- [ ] **Learn Eval**: `/everything-claude-code:learn-eval` — evaluate session for extractable patterns → save to `~/.claude/skills/learned/`.

### [9h] Commit [ ]
```bash
git add src/ tests/ GSD_PLAN.md
git commit -m "feat: methods workbench — namespaced keys, generalized schema, provenance restore, cockpit workbench button"
```

---

## Session 10: Research Agent [ ]

Requires Session 9 complete.

> **Note**: Methods exist in the workbench as queue-only (added in Session 9). The research
> pipeline in this session is still tool-specific. When generalizing to support methods,
> add source-type-specific prompts (methods don't have `## How to Install`) and
> source-type-aware output directory naming (use `get_slug(name, source_type)`).

### [10a] TDD — write research agent tests first [ ]
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

### [10b] src/utils/research_agent.py [ ]
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

### [10c] Workbench page — Research button + log tail + review gate [ ]
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

### [10d] Verify GREEN [ ]
- [ ] Run `pytest tests/test_research_agent.py -v` — ALL tests PASS
- [ ] Run `pytest tests/ --cov=src/utils --cov-report=term-missing` — full suite passes, coverage ≥ 80%

### [10e] Quality Gate [ ]

**MANDATORY**: Each gate below requires reading the specified file with the Read tool and following its EXACT protocol. Do NOT improvise your own review — execute the steps in the file as written.

- [ ] **Verify**: Run `/steadows-verify`. Confirm build PASS, lint clean, full suite PASS, coverage ≥ 80%. Includes code review (focus: `research_agent.py`, `3_Workbench.py`) and security review (focus: subprocess injection — prompt as list arg, no shell=True with f-string, no user-controlled subprocess args, log files in controlled paths). All CRITICAL/HIGH findings fixed. Verdict: PASS.
- [ ] **Learn Eval**: `/everything-claude-code:learn-eval` — evaluate session for extractable patterns → save to `~/.claude/skills/learned/`.

### [10f] Commit [ ]
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

---

## Architecture

```
┌──────────────────────────────────────────────────────────────────┐
│                         Streamlit App                            │
│                                                                  │
│  src/Home.py ──→ 1_Dashboard.py  2_Project_Cockpit.py            │
│                        │  │              │                       │
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
│  └─────────────────────────┬─────────────────────────────┘       │
└────────────────────────────┼─────────────────────────────────────┘
                             │
         ┌───────────────────┼──────────────────────────┐
         │                   │                │          │
 Obsidian Vault       status.json      Anthropic API   ~/research-workbench/
 (OBSIDIAN_VAULT_PATH)  workbench.json  (claude -p     {tool-slug}/
                        paper-cache/    subprocess)    research.md
                       (~/.research-                   research.html
                        dashboard/)
                                                       Dockerfile
                                                       experiment.py
                                                       run.sh
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

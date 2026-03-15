# GSD Plan: Research Intelligence Dashboard

> **Created:** 2026-03-14 | **Revised:** 2026-03-15 | **Stack:** Python 3.11 · Streamlit · Anthropic SDK · PyYAML
> **Reference:** `Plans/Research Intelligence System.md` (Obsidian) — full design spec

---

## 0. Execution Model

**One Ralph Loop per session.** Each GSD session (1–6) runs in its own Claude Code context window.

```bash
# Operator runs one session at a time:
/ralph-loop "Execute Session N of GSD_PLAN.md. Read GSD_PLAN.md and CLAUDE.md first. Mark tasks [ ] when starting, [ ] when done. Follow TDD per ~/.claude/skills/tdd-workflow/SKILL.md. Run ALL quality gate sub-tasks listed in the session. Conda env: /opt/anaconda3/envs/research-dashboard. Vault: /Users/stevemeadows/SteveVault. API key: .env.local CLAUDE_API_KEY (load as ANTHROPIC_API_KEY). Output <promise>SESSION N COMPLETE</promise> when all tasks in Session N are [ ]." --max-iterations 10 --completion-promise "SESSION N COMPLETE"
```

After each session completes, start a **new** Claude Code session for the next one.

Sessions 3 and 4 can run concurrently (separate terminal windows) after Session 2.

---

## 1. Quality Gate Skills

| Skill | File Path |
|-------|-----------|
| TDD Workflow | `~/.claude/skills/tdd-workflow/SKILL.md` |
| Code Review | `~/.claude/commands/code-review.md` |
| Verify | `~/.claude/skills/verify/SKILL.md` |
| Security Review | `~/.claude/skills/security-review/SKILL.md` |
| LLM Trace | `~/.claude/skills/streamlit-llm-trace/SKILL.md` |
| Claude API | `~/.claude/skills/claude-api/SKILL.md` |
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

### [6h] Commit [~]
```bash
git add src/ tests/ .streamlit/ requirements.txt .env.example GSD_PLAN.md CLAUDE.md
git commit -m "feat: research intelligence dashboard — dashboard + cockpit views with Claude API analysis"
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

---

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    Streamlit App                        │
│                                                         │
│  src/Home.py ──→ 1_Dashboard.py   2_Project_Cockpit.py  │
│                        │                   │            │
│                        └──────┬────────────┘            │
│                               │                         │
│                        src/utils/                       │
│  ┌────────────────────────────────────────────────┐     │
│  │ vault_parser  methods_parser  tools_parser     │     │
│  │ blog_queue_parser  reports_parser              │     │
│  │ status_tracker  claude_client  prompt_builder  │     │
│  │ cockpit_components  parser_helpers             │     │
│  └──────────────────────────┬─────────────────────┘     │
└─────────────────────────────┼───────────────────────────┘
                              │
              ┌───────────────┼───────────────┐
              │               │               │
    Obsidian Vault     status.json      Anthropic API
    (OBSIDIAN_VAULT_PATH)  (~/.research-  (ANTHROPIC_API_KEY)
                           dashboard/)
```

---

## Files Changed Summary

| File | Session | Purpose |
|------|---------|---------|
| `src/Home.py` | 1 | Entry point, nav, CSS, env validation |
| `.streamlit/config.toml` | 1 | Dark OLED theme |
| `src/utils/parser_helpers.py` | 2 | Shared parsing utilities (DRY) |
| `src/utils/vault_parser.py` | 2 | Project parsing + wiki-links |
| `src/utils/methods_parser.py` | 2 | Methods backlog parser |
| `src/utils/tools_parser.py` | 2 | Tools radar parser |
| `src/utils/blog_queue_parser.py` | 2 | Blog queue parser |
| `src/utils/reports_parser.py` | 2 | JournalClub + TLDR parser |
| `src/utils/status_tracker.py` | 2 | Status + analysis cache |
| `src/utils/page_helpers.py` | 3 | Shared page utilities |
| `src/pages/1_Dashboard.py` | 3 | Global intel feed — 5 tabs |
| `src/utils/claude_client.py` | 4 | Anthropic SDK wrapper + LLM trace |
| `src/utils/prompt_builder.py` | 4 | Prompt construction |
| `src/pages/2_Project_Cockpit.py` | 5 | Project-scoped workspace |
| `src/utils/cockpit_components.py` | 5 | Cockpit UI components |
| `tests/test_integration.py` | 6 | Round-trip pipeline tests |

---

## Risk Register

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|-----------|
| Vault format changes | Medium | Medium | Regex with fallbacks; log warnings |
| API latency on Analyze | High | Low | Haiku fast (~1s); spinner covers UX |
| Status.json corruption | Low | Low | Atomic write via temp + `os.replace()` |
| Wiki-link name drift | Low | High | Index from filenames; log mismatches |
| Vault path with spaces | Medium | Medium | `pathlib.Path` throughout |

# CLAUDE.md

This file provides guidance to Claude Code when working with code in this repository.

## Project Overview

Research Intelligence Dashboard — a Streamlit app that surfaces actionable insights from automated newsletter ingestion (JournalClub, TLDR). Two views: a global **Dashboard** (blog queue, tools radar, research archive, weekly AI signal) and a **Project Cockpit** (project-scoped workspace with Claude API analysis).

Data flows from scheduled tasks (Gmail → Obsidian vault) through markdown parsers into the Streamlit UI. Claude API (Haiku for quick analysis, Sonnet for deep) provides on-demand item-to-project relevance scoring.

## Development Commands

```bash
# Activate environment
conda activate research-dashboard

# Run locally
cd src && streamlit run Home.py

# Run tests
pytest tests/ -v --tb=short

# Run tests with coverage
pytest tests/ --cov=src/utils --cov-report=term-missing

# Lint
ruff check src/ tests/
ruff format src/ tests/
```

## Architecture

### Multipage Streamlit App
- `src/Home.py` — Entry point, nav shell, CSS injection, env validation
- `src/pages/1_Dashboard.py` — Global intel feed with 5 tabs (Home, Blog Queue, Tools Radar, Research Archive, Weekly AI Signal)
- `src/pages/2_Project_Cockpit.py` — Project-scoped workspace with Analyze/Go Deep buttons

### Core Utilities (`src/utils/`)
- `vault_parser.py` — Obsidian vault project parsing, wiki-link extraction, project index builder
- `methods_parser.py` — Parses `Research/Methods to Try.md` into structured items
- `tools_parser.py` — Parses `Research/Tools Radar.md` into structured items
- `blog_queue_parser.py` — Parses `Writing/Blog Queue.md` into structured items
- `reports_parser.py` — Parses `Research/JournalClub/*.md` and `Research/TLDR/*.md` archives
- `status_tracker.py` — JSON-based status + analysis cache (`~/.research-dashboard/status.json`)
- `claude_client.py` — Anthropic SDK wrapper with LLM trace logging
- `prompt_builder.py` — Prompt construction for quick/deep analysis
- `cockpit_components.py` — Reusable Project Cockpit UI components

### Data Flow
1. **Scheduled tasks** (Monday 7:30am JournalClub, Friday 8am TLDR) write markdown to Obsidian vault
2. **Parsers** read vault markdown files, extract structured data + wiki-links
3. **Project index** maps `[[Project Name]]` wiki-links → items per project
4. **Dashboard** renders global feeds; **Cockpit** renders project-scoped feeds
5. **Claude API** provides on-demand analysis (Haiku quick, Sonnet deep) with response caching

### Key Data Sources (Obsidian Vault)
- `Projects/*.md` — Project pages (frontmatter + content)
- `Research/Methods to Try.md` — JournalClub methods backlog
- `Research/Tools Radar.md` — TLDR tools backlog
- `Writing/Blog Queue.md` — Blog ideas queue
- `Research/JournalClub/*.md` — Weekly JournalClub reports
- `Research/TLDR/*.md` — Weekly TLDR synthesis reports
- `Plans/*.md` — GSD plans for projects

## Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `OBSIDIAN_VAULT_PATH` | Yes | Absolute path to Obsidian vault (e.g., `/Users/stevemeadows/SteveVault`) |
| `ANTHROPIC_API_KEY` | Yes | Anthropic API key for Claude |
| `LLM_TRACE` | No | Set to `1` to enable LLM I/O trace logging (debug only) |

## GSD Workflow

This project follows the GSD protocol. The implementation plan lives at `GSD_PLAN.md` in the project root.

1. Review `GSD_PLAN.md` before starting any task
2. Update task status immediately: `[ ]` → `[~]` → `[x]` or `[!]`
3. Respect the dependency graph — Sessions 3+4 can run concurrently after Session 2
4. Run quality gates at the end of each session

## Design System

- **Style:** Dark OLED
- **Background:** `#0A0A0A` | **Surface:** `#111827` | **Border:** `#1F2937`
- **Primary:** `#1E40AF` | **Accent:** `#3B82F6` | **CTA:** `#F59E0B`
- **Heading font:** Exo (300/400/600/700) | **Body font:** Roboto Mono (400/500)
- **Transitions:** 150–300ms | **Contrast:** WCAG AA minimum (4.5:1)

## Code Conventions

- Type hints on all function signatures
- Docstrings on all public functions and classes
- Functions under 50 lines — extract helpers when exceeding
- `pathlib.Path` for all file operations (never `os.path`)
- `@st.cache_data(ttl=3600)` on all parser functions
- Module-level logger: `logger = logging.getLogger(__name__)`
- Session state keys namespaced: `dashboard__*`, `cockpit__*`
- Never call Claude API directly from page files — route through `claude_client.py`
- Immutable data patterns — return new objects, never mutate

## Streamlit Skills Reference

When working on Streamlit features, consult the skill files in `~/.claude/skills/developing-with-streamlit/`:

| Task | Skill |
|------|-------|
| Dashboards, KPI cards, metrics | `building-streamlit-dashboards` |
| Multipage app architecture | `building-streamlit-multipage-apps` |
| LLM output theming, structured output, cost tracking | `building-streamlit-llm-apps` |
| Themes, colors, fonts | `creating-streamlit-themes` |
| Performance, caching, fragments | `optimizing-streamlit-performance` |
| Design, icons, badges, visual polish | `improving-streamlit-design` |
| Session state, widget keys, callbacks | `using-streamlit-session-state` |
| Widget double-click bugs, key-only pattern | `avoiding-streamlit-widget-pitfalls` |
| Layouts, sidebar, columns, tabs | `using-streamlit-layouts` |
| Selection widgets (selectbox, toggle, etc.) | `choosing-streamlit-selection-widgets` |
| Data display, dataframes, charts | `displaying-streamlit-data` |
| Code organization, splitting modules | `organizing-streamlit-code` |

Parent skill with routing guide: `~/.claude/skills/developing-with-streamlit/SKILL.md`

## LLM Trace Logging

Per `/streamlit-llm-trace` skill:
- Use a dedicated logger: `_llm_trace_log = logging.getLogger("llm_trace")`
- `_llm_trace_log.propagate = False` — **CRITICAL**, prevents CloudWatch bleed-through
- Before call: log full prompt at DEBUG (LLM_TRACE=1 only)
- After call: log model, token counts, cost estimate at INFO
- On error: log full prompt + error at WARNING

## Testing

- TDD workflow: write tests first (RED), implement (GREEN), refactor
- Minimum coverage target: 80%
- Capturing mocks at filesystem boundary (vault reads) and Claude API boundary
- Test files: `tests/test_*.py`
- Round-trip integration tests verify full pipeline: vault → parser → index → cockpit feed

## Git Conventions

- Do NOT include `Co-Authored-By` trailers in commits
- Atomic commits — one logical change per commit
- Conventional commit messages: `feat:`, `fix:`, `refactor:`, `docs:`, `test:`, `chore:`

# CLAUDE.md

This file provides guidance to Claude Code when working with code in this repository.

## Project Overview

Research Intelligence Dashboard — surfaces actionable insights from automated newsletter ingestion (JournalClub, TLDR, Instagram). FastAPI backend (`api/`) + Next.js frontend (`web/`) with Claude API for on-demand relevance scoring and deep analysis.

Data flows from scheduled tasks (Gmail → Obsidian vault) through shared parsers (`src/utils/`) into the FastAPI layer, then consumed by the Next.js frontend.

## Development Commands

```bash
# Activate environment
conda activate research-dashboard

# Run locally (FastAPI :8000, Next.js :3000)
./scripts/dev.sh

# Run in production mode (Next.js :3001, FastAPI :8000, Caddy :3000)
./scripts/start.sh

# Run tests
pytest tests/ -v --tb=short

# Run tests with coverage
pytest tests/ --cov=src/utils --cov-report=term-missing

# Lint
ruff check src/ tests/
ruff format src/ tests/
```

## Architecture

### Dual-Stack Application

- **FastAPI** (`api/`) — REST/WebSocket API layer; imports parsers and business logic from `src/utils/`
- **Next.js** (`web/`) — React frontend (Tailwind v4, shadcn/ui) consuming FastAPI endpoints
- **Shared utilities** (`src/utils/`) — Decoupled from any frontend framework; used by both layers
- **Legacy pages** (`src/legacy_pages/`) — Retired Streamlit pages kept for reference

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
- `page_helpers.py` — Pure utility functions
- `smart_matcher.py` — Hybrid item-to-project matching (uses cachetools)

### Data Flow
1. **Scheduled tasks** (Monday 7:30am JournalClub, Friday 8am TLDR) write markdown to Obsidian vault
2. **Parsers** read vault markdown files, extract structured data + wiki-links
3. **Project index** maps `[[Project Name]]` wiki-links → items per project
4. **FastAPI** exposes parsed data via REST endpoints; WebSocket for live updates
5. **Next.js** renders global feeds and project cockpit views
6. **Claude API** provides on-demand analysis (Haiku quick, Sonnet deep) with response caching

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
| `API_BACKEND_URL` | No | Override FastAPI base URL (default: `http://localhost:8000`) |
| `NEXT_PUBLIC_WS_URL` | No | Override WebSocket URL (default: `ws://localhost:8000`) |

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
- `cachetools.TTLCache` for caching in shared modules
- Module-level logger: `logger = logging.getLogger(__name__)`
- Never call Claude API directly from route handlers — route through `claude_client.py`
- Immutable data patterns — return new objects, never mutate

## Frontend Skills Reference

| Skill | Purpose |
|-------|---------|
| `framer-motion-animator` | Animation patterns for effects components |
| `framer-motion` | 42 performance rules (LazyMotion, useMotionValue, etc.) |
| `tailwind-v4-shadcn` | Tailwind v4 setup, 4-step architecture |
| `d3-viz` | D3.js visualization patterns |

## Design System Reference

Full design token spec lives at `docs/designs/DESIGN_SYSTEM.md`. Includes glow system, component rules, and visual references for the Next.js frontend.

## LLM Trace Logging

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
- Round-trip integration tests verify full pipeline: vault → parser → index → API response

## Git Conventions

- Do NOT include `Co-Authored-By` trailers in commits
- Atomic commits — one logical change per commit
- Conventional commit messages: `feat:`, `fix:`, `refactor:`, `docs:`, `test:`, `chore:`

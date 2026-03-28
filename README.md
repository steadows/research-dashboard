# Research Intelligence Dashboard (R.I.D.)

Surfaces actionable insights from automated newsletter ingestion (JournalClub, TLDR, Instagram). A FastAPI backend exposes parsed Obsidian vault data via REST and WebSocket endpoints; a Next.js frontend consumes those endpoints and calls the Claude API for on-demand relevance scoring and deep analysis. Shared utilities in `src/utils/` are decoupled from any frontend framework and reused by both layers.

## Architecture

```
web/          Next.js frontend (React, Tailwind v4, shadcn/ui)
api/          FastAPI backend (REST + WebSocket)
src/utils/    Shared parsers and business logic
src/legacy_pages/  Legacy Streamlit pages (reference only)
```

The FastAPI layer (`api/`) imports parsers from `src/utils/` directly. The Next.js frontend (`web/`) proxies through Caddy in production, talking to both FastAPI (:8000) and the Next.js server (:3001).

## Prerequisites

- Python 3.11+
- Node.js 20+
- conda environment: `research-dashboard`
- Caddy (production / macOS app only): `brew install caddy`

## Setup

```bash
conda activate research-dashboard
pip install -r requirements.txt
cd web && npm install && cd ..
cp .env.example .env.local  # fill in OBSIDIAN_VAULT_PATH and ANTHROPIC_API_KEY
```

## Development

```bash
./scripts/dev.sh
```

Starts FastAPI on `:8000` and Next.js on `:3000`.

## Production

```bash
./scripts/start.sh
caddy run --config scripts/Caddyfile
```

- Caddy: `:3000` (reverse proxy)
- Next.js: `:3001`
- FastAPI: `:8000`

## macOS App

```bash
./scripts/build-app.sh
# Output: dist/Research Dashboard.app
```

Requires `brew install caddy`. The app bundle wraps Caddy, Next.js, and FastAPI into a single launchable `.app`.

## Testing

```bash
# Python — 525 tests
pytest tests/ -v --tb=short

# Frontend — 164 tests
cd web && npm test

# E2E
cd web && npx playwright test
```

## Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `OBSIDIAN_VAULT_PATH` | Yes | Absolute path to Obsidian vault (e.g., `/Users/stevemeadows/SteveVault`) |
| `ANTHROPIC_API_KEY` | Yes | Anthropic API key for Claude |
| `LLM_TRACE` | No | Set to `1` to enable LLM I/O trace logging (debug only) |
| `API_BACKEND_URL` | No | Override FastAPI base URL (default: `http://localhost:8000`) |
| `NEXT_PUBLIC_WS_URL` | No | Override WebSocket URL (default: `ws://localhost:8000`) |

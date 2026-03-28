#!/usr/bin/env bash
# dev.sh — Start FastAPI + Next.js dev servers with hot reload.
# Usage: ./scripts/dev.sh (from repo root)
# Requires: conda env "research-dashboard", OBSIDIAN_VAULT_PATH set in .env.local
#
# IMPORTANT: uvicorn must run with --workers 1 (in-memory job state is
# single-process only). Do not change this without updating the linker router.

set -euo pipefail
cd "$(dirname "$0")/.."

# Source env if available
[[ -f .env.local ]] && set -a && source .env.local && set +a

echo "[dev] Starting FastAPI on :8000 and Next.js on :3000"

# FastAPI — single worker required for in-memory job state
uvicorn api.main:app --host 127.0.0.1 --port 8000 --reload --workers 1 &
API_PID=$!

# Next.js dev server
cd web && npm run dev &
WEB_PID=$!
cd ..

trap 'echo "[dev] Shutting down..."; kill $API_PID $WEB_PID 2>/dev/null; wait' SIGINT SIGTERM

echo "[dev] API PID=$API_PID, Web PID=$WEB_PID"
echo "[dev] Dashboard: http://localhost:3000"
wait $API_PID $WEB_PID

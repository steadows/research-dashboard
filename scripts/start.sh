#!/usr/bin/env bash
# start.sh — Start FastAPI + Next.js in production mode (serve only, no build).
# Usage: ./scripts/start.sh (from repo root)
# Requires: `cd web && npm run build` to have been run first.
#
# IMPORTANT: uvicorn must run with --workers 1 (in-memory job state is
# single-process only). Do not change this without updating the linker router.

set -euo pipefail
cd "$(dirname "$0")/.."

# Source env if available
[[ -f .env.local ]] && set -a && source .env.local && set +a

echo "[start] Starting FastAPI on :8000 and Next.js on :3001"

# FastAPI — single worker required for in-memory job state
uvicorn api.main:app --host 127.0.0.1 --port 8000 --workers 1 &
API_PID=$!

# Next.js production server on :3001 (Caddy owns :3000 in prod)
cd web && PORT=3001 npm start &
WEB_PID=$!
cd ..

trap 'echo "[start] Shutting down..."; kill $API_PID $WEB_PID 2>/dev/null; wait' SIGINT SIGTERM

echo "[start] API PID=$API_PID, Web PID=$WEB_PID"
wait $API_PID $WEB_PID

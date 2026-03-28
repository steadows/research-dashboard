#!/usr/bin/env bash
set -euo pipefail

# launcher.sh — macOS .app bundle entrypoint for Research Intelligence Dashboard
# Manages startup of: uvicorn + Next.js (via start.sh) and Caddy (reverse proxy)
# This script is copied into Contents/MacOS/launcher by build-app.sh

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# ---------------------------------------------------------------------------
# 1. Resolve project root from .launcher-config written by build-app.sh
# ---------------------------------------------------------------------------
LAUNCHER_CONFIG="$SCRIPT_DIR/../Resources/.launcher-config"

if [[ ! -f "$LAUNCHER_CONFIG" ]]; then
  osascript -e 'display dialog "Research Dashboard: .launcher-config not found. Please rebuild the app using build-app.sh." with title "Launch Error" buttons {"OK"} default button "OK" with icon stop'
  exit 1
fi

# shellcheck source=/dev/null
source "$LAUNCHER_CONFIG"

if [[ -z "${PROJECT_ROOT:-}" ]]; then
  osascript -e 'display dialog "Research Dashboard: PROJECT_ROOT not set in .launcher-config. Please rebuild the app." with title "Launch Error" buttons {"OK"} default button "OK" with icon stop'
  exit 1
fi

# ---------------------------------------------------------------------------
# 2. Verify project root is valid
# ---------------------------------------------------------------------------
if [[ ! -f "$PROJECT_ROOT/api/main.py" ]]; then
  osascript -e "display dialog \"Research Dashboard: Project root not found or invalid.\n\nExpected: $PROJECT_ROOT/api/main.py\n\nPlease rebuild the app from the correct project directory.\" with title \"Launch Error\" buttons {\"OK\"} default button \"OK\" with icon stop"
  exit 1
fi

# ---------------------------------------------------------------------------
# 3. Discover and activate conda environment (must happen before caddy check,
#    since caddy may be installed inside the conda env)
# ---------------------------------------------------------------------------
CONDA_SH=""

find_conda_sh() {
  local candidates=(
    "${CONDA_EXE:+$(dirname "$(dirname "$CONDA_EXE")")/etc/profile.d/conda.sh}"
    "/opt/anaconda3/etc/profile.d/conda.sh"
    "/opt/homebrew/Caskroom/miniconda/base/etc/profile.d/conda.sh"
    "$HOME/miniconda3/etc/profile.d/conda.sh"
    "$HOME/anaconda3/etc/profile.d/conda.sh"
  )
  for candidate in "${candidates[@]}"; do
    if [[ -n "$candidate" && -f "$candidate" ]]; then
      echo "$candidate"
      return 0
    fi
  done
  return 1
}

if ! CONDA_SH="$(find_conda_sh)"; then
  osascript -e 'display dialog "Research Dashboard: Could not find conda.\n\nInstall Miniconda from https://docs.conda.io/en/latest/miniconda.html and ensure the research-dashboard environment exists.\n\nSearched:\n• /opt/anaconda3/\n• /opt/homebrew/Caskroom/miniconda/base/\n• ~/miniconda3/\n• ~/anaconda3/" with title "conda Not Found" buttons {"OK"} default button "OK" with icon stop'
  exit 1
fi

# shellcheck source=/dev/null
source "$CONDA_SH"
conda activate research-dashboard

# ---------------------------------------------------------------------------
# 4. Check Caddy is installed (after conda activation — caddy may be in env)
# ---------------------------------------------------------------------------
if ! command -v caddy &>/dev/null; then
  osascript -e 'display dialog "Research Dashboard requires Caddy as a reverse proxy.\n\nInstall with:\n    conda install -c conda-forge caddy\n\nThen relaunch the app." with title "Missing Dependency: caddy" buttons {"OK"} default button "OK" with icon stop'
  exit 1
fi

# ---------------------------------------------------------------------------
# 5. Source .env.local if present
# ---------------------------------------------------------------------------
if [[ -f "$PROJECT_ROOT/.env.local" ]]; then
  # shellcheck source=/dev/null
  set -a
  source "$PROJECT_ROOT/.env.local"
  set +a
fi

# ---------------------------------------------------------------------------
# 6. Health-based port check — detect if RID is already running
# ---------------------------------------------------------------------------
ports_in_use() {
  lsof -ti :3000 &>/dev/null && lsof -ti :3001 &>/dev/null && lsof -ti :8000 &>/dev/null
}

check_rid_healthy() {
  local frontend_ok api_ok
  frontend_ok=$(curl -s -o /dev/null -w "%{http_code}" --max-time 3 http://localhost:3000 2>/dev/null || echo "000")
  api_ok=$(curl -s -o /dev/null -w "%{http_code}" --max-time 3 http://localhost:8000/api/papers 2>/dev/null || echo "000")
  [[ "$frontend_ok" =~ ^[2-3][0-9][0-9]$ ]] && [[ "$api_ok" =~ ^[2-3][0-9][0-9]$ ]]
}

if ports_in_use; then
  if check_rid_healthy; then
    # Already running and healthy — just open the browser
    if open -a "Google Chrome" --args --app=http://localhost:3000 2>/dev/null; then
      :
    else
      open http://localhost:3000
    fi
    exit 0
  else
    osascript -e 'display dialog "Research Dashboard: Ports 3000, 3001, and 8000 are in use but the servers are not responding as expected.\n\nAnother process may be occupying these ports. Free the ports and try again." with title "Port Conflict" buttons {"OK"} default button "OK" with icon stop'
    exit 1
  fi
fi

# ---------------------------------------------------------------------------
# 7. PID tracking and cleanup trap
# ---------------------------------------------------------------------------
START_PID=""
CADDY_PID=""

cleanup() {
  if [[ -n "$START_PID" ]]; then
    kill -TERM "$START_PID" 2>/dev/null || true
  fi
  if [[ -n "$CADDY_PID" ]]; then
    kill -TERM "$CADDY_PID" 2>/dev/null || true
  fi
}

trap cleanup SIGTERM SIGINT

# ---------------------------------------------------------------------------
# 8. Launch servers
# ---------------------------------------------------------------------------
cd "$PROJECT_ROOT"
bash "$PROJECT_ROOT/scripts/start.sh" &
START_PID=$!

caddy run --config "$PROJECT_ROOT/scripts/Caddyfile" &
CADDY_PID=$!

# ---------------------------------------------------------------------------
# 9. Poll readiness — both frontend (Caddy :3000) and API (:8000) must respond
# ---------------------------------------------------------------------------
TIMEOUT=60
INTERVAL=1
elapsed=0
frontend_ready=false
api_ready=false

while (( elapsed < TIMEOUT )); do
  if ! frontend_ready; then
    if curl -s -o /dev/null -w "%{http_code}" --max-time 2 http://localhost:3000 2>/dev/null | grep -qE '^[2-3][0-9][0-9]$'; then
      frontend_ready=true
    fi
  fi

  if ! api_ready; then
    if curl -s -o /dev/null -w "%{http_code}" --max-time 2 http://localhost:8000/api/papers 2>/dev/null | grep -qE '^[2-3][0-9][0-9]$'; then
      api_ready=true
    fi
  fi

  if $frontend_ready && $api_ready; then
    break
  fi

  sleep "$INTERVAL"
  (( elapsed += INTERVAL )) || true
done

# ---------------------------------------------------------------------------
# 10. Handle partial or full startup failure
# ---------------------------------------------------------------------------
if ! $frontend_ready || ! $api_ready; then
  failed_servers=""
  if ! $frontend_ready; then
    failed_servers="• Frontend (localhost:3000 via Caddy)"
  fi
  if ! $api_ready; then
    failed_servers="${failed_servers:+$failed_servers\n}• API (localhost:8000)"
  fi

  cleanup

  osascript -e "display dialog \"Research Dashboard failed to start within ${TIMEOUT}s.\n\nServers that did not respond:\n${failed_servers}\n\nCheck Console.app for details.\" with title \"Startup Failure\" buttons {\"OK\"} default button \"OK\" with icon stop"
  exit 1
fi

# ---------------------------------------------------------------------------
# 11. Open PWA-style chromeless window
# ---------------------------------------------------------------------------
if open -a "Google Chrome" --args --app=http://localhost:3000 2>/dev/null; then
  :
else
  open http://localhost:3000
fi

# ---------------------------------------------------------------------------
# 12. Wait for child processes (keeps launcher alive so trap fires on quit)
# ---------------------------------------------------------------------------
wait "$START_PID" "$CADDY_PID" 2>/dev/null || true

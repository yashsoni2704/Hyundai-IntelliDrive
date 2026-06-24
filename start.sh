#!/usr/bin/env bash
# Render start script — always bind 0.0.0.0:$PORT (never hard-code 8000).
set -euo pipefail

ROOT="$(cd "$(dirname "$0")" && pwd)"
PORT="${PORT:-10000}"

echo "=== start.sh === PORT=$PORT root=$ROOT"

if [[ -f "$ROOT/backend/run.py" ]]; then
  exec python "$ROOT/backend/run.py"
fi

exec python "$ROOT/run_render.py"

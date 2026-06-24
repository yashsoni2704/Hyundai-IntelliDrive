#!/usr/bin/env bash
# Render start script — bind to Render's dynamic PORT immediately.
set -euo pipefail
cd "$(dirname "$0")"
exec uvicorn app:app --host 0.0.0.0 --port "${PORT:-8000}"

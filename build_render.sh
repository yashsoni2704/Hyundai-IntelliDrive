#!/usr/bin/env bash
# Render build: install deps + pre-build FAQ index (keeps runtime memory low).
set -euo pipefail

ROOT="$(cd "$(dirname "$0")" && pwd)"

echo "=== Installing Python dependencies ==="
pip install -r "$ROOT/requirements.txt"

echo "=== Building React frontend (served from Render + fixes Vercel lag) ==="
cd "$ROOT/frontend"
if command -v npm >/dev/null 2>&1; then
  npm ci
  npm run build
  echo "Frontend built to frontend/dist"
else
  echo "WARNING: npm not found — skipping frontend build"
fi
cd "$ROOT"

echo "=== Pre-building knowledge base (keyword mode for 512 MB free tier) ==="
export LIGHTWEIGHT_MODE="${LIGHTWEIGHT_MODE:-true}"
export OMP_NUM_THREADS="${OMP_NUM_THREADS:-1}"
export MKL_NUM_THREADS="${MKL_NUM_THREADS:-1}"
export TOKENIZERS_PARALLELISM="${TOKENIZERS_PARALLELISM:-false}"
python "$ROOT/scripts/prebuild_chroma.py"

echo "=== Build complete ==="

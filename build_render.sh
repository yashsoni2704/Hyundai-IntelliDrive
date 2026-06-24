#!/usr/bin/env bash
# Render build: compile React frontend + install Python backend deps.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")" && pwd)"

# echo "=== Building React frontend ==="
# cd "$ROOT/frontend"
# npm ci
# VITE_API_URL= npm run build

echo "=== Installing Python dependencies ==="
pip install -r "$ROOT/requirements.txt"

echo "=== Build complete ==="

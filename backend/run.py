#!/usr/bin/env python3
"""
Render.com entrypoint when Root Directory is set to backend/.

Binds to host 0.0.0.0 and the PORT environment variable (Render sets this).
"""

from __future__ import annotations

import os
import sys

print("=== Hyundai Knowledge Assistant — backend/run.py ===", flush=True)
print(f"PORT={os.environ.get('PORT', 'NOT SET')}", flush=True)
print(f"cwd={os.getcwd()}", flush=True)

raw_port = os.environ.get("PORT", "10000").strip()
try:
    port = int(raw_port)
except ValueError:
    print(f"FATAL: PORT is not a valid integer: {raw_port!r}", flush=True)
    sys.exit(1)

host = "0.0.0.0"
print(f"Starting uvicorn on http://{host}:{port}", flush=True)

import uvicorn

uvicorn.run(
    "app:app",
    host=host,
    port=port,
    log_level="info",
    access_log=True,
    proxy_headers=True,
    forwarded_allow_ips="*",
)

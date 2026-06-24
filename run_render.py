#!/usr/bin/env python3
"""
Render.com entrypoint when Root Directory is empty (repo root).

Render requires:
  - bind to host 0.0.0.0
  - bind to the port in the PORT environment variable
"""

from __future__ import annotations

import os
import sys
from pathlib import Path


def main() -> None:
    print("=== Hyundai Knowledge Assistant — Render boot ===", flush=True)
    print(f"PORT={os.environ.get('PORT', 'NOT SET')}", flush=True)

    root = Path(__file__).resolve().parent
    backend = root / "backend"

    if not backend.is_dir():
        print(f"FATAL: backend directory missing: {backend}", flush=True)
        sys.exit(1)

    os.chdir(backend)
    sys.path.insert(0, str(backend))
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


if __name__ == "__main__":
    main()

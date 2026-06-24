"""
Render entrypoint for the FastAPI app.

Render starts from the repository root, while the real application lives in
`backend/app.py` and imports sibling backend modules like `config.py`,
`database.py`, and `chroma_db.py`.

This shim adds `backend/` to `sys.path`, then loads the real FastAPI `app`
object from `backend/app.py` so `uvicorn app:app` works from the repo root.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent
BACKEND_DIR = PROJECT_ROOT / "backend"
BACKEND_APP = BACKEND_DIR / "app.py"

if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

spec = importlib.util.spec_from_file_location("backend_main_app", BACKEND_APP)
if spec is None or spec.loader is None:
    raise RuntimeError(f"Unable to load backend app from {BACKEND_APP}")

module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)

app = module.app

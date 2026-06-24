#!/usr/bin/env python3
"""Pre-build ChromaDB during Render deploy (avoids memory spike at runtime)."""

import os
import sys
from pathlib import Path

backend = Path(__file__).resolve().parent.parent / "backend"
sys.path.insert(0, str(backend))
os.chdir(backend)

from chroma_db import get_vector_store

store = get_vector_store()
store.initialize_safe()

if store.init_error:
    print(f"Chroma prebuild FAILED: {store.init_error}", flush=True)
    sys.exit(1)

print(
    f"Chroma prebuild OK: {store.document_count} documents "
    f"(lightweight={os.getenv('LIGHTWEIGHT_MODE', 'false')})",
    flush=True,
)

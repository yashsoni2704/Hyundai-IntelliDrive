"""
Application configuration — loads environment variables from backend/.env.

All paths are absolute (resolved from PROJECT_ROOT) so the app works
regardless of which directory you start uvicorn from.

Key settings:
  - EXCEL_PATH: source FAQ data
  - CHROMA_PERSIST_DIR: vector database storage on disk
  - SIMILARITY_THRESHOLD: minimum cosine similarity to return an answer (0.55)
  - JWT_* / SMTP_*: authentication and Brevo email OTP
"""

import os
from pathlib import Path

from dotenv import load_dotenv

# BASE_DIR = backend/ folder; PROJECT_ROOT = Hyundai_chatbot/ folder
BASE_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = BASE_DIR.parent
load_dotenv(BASE_DIR / ".env", override=False)  # never override Render/platform env vars

# --- File paths ---
DATA_DIR = PROJECT_ROOT / "data"
FRONTEND_DIST = PROJECT_ROOT / "frontend" / "dist"
EXCEL_PATH = DATA_DIR / "hyundai_faq.xlsx"
CHROMA_PERSIST_DIR = BASE_DIR / "chroma_db"
INGESTION_META_PATH = CHROMA_PERSIST_DIR / "ingestion_meta.json"
DATABASE_URL = f"sqlite:///{BASE_DIR / 'app.db'}"  # SQLite file-based database

# Warn at import time instead of crashing — lets /health respond on Render
if not EXCEL_PATH.exists():
    import warnings

    warnings.warn(
        f"FAQ Excel file not found: {EXCEL_PATH}. "
        "Knowledge-base endpoints will fail until data/hyundai_faq.xlsx is present.",
        stacklevel=1,
    )

# --- ChromaDB ---
COLLECTION_NAME = os.getenv("COLLECTION_NAME", "hyundai_faq")

# --- Embeddings (Hugging Face model name) ---
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "BAAI/bge-m3")

# Render free tier (512 MB): skip PyTorch/sentence-transformers; use keyword FAQ search.
LIGHTWEIGHT_MODE = os.getenv("LIGHTWEIGHT_MODE", "false").lower() == "true"

# Chroma cosine distance = 1 - cosine_similarity; threshold 0.55 ≈ reasonably confident match
SIMILARITY_THRESHOLD = float(os.getenv("SIMILARITY_THRESHOLD", "0.55"))

# --- JWT authentication ---
JWT_SECRET = os.getenv("JWT_SECRET", "hyundai-dev-secret-change-in-production")
JWT_ALGORITHM = "HS256"
JWT_EXPIRE_MINUTES = int(os.getenv("JWT_EXPIRE_MINUTES", "1440"))  # 24 hours

# --- Brevo email (https://app.brevo.com/settings/keys) ---
SMTP_HOST = os.getenv("SMTP_HOST") or os.getenv("SMTP_SERVER", "smtp-relay.brevo.com")
_default_smtp_port = "2525" if os.getenv("RENDER") else "587"
SMTP_PORT = int(os.getenv("SMTP_PORT", _default_smtp_port))
SMTP_USER = os.getenv("SMTP_USER") or os.getenv("LOGIN", "")


def _clean_key(value: str) -> str:
    return value.strip().strip('"').strip("'").strip()


def _scan_env_keys() -> tuple[str, str]:
    """Find Brevo API key (xkeysib) and SMTP key (xsmtpsib) from any common env var."""
    api_key = ""
    smtp_key = ""
    for name, value in os.environ.items():
        if not value:
            continue
        cleaned = _clean_key(value)
        if cleaned.startswith("xkeysib-") and not api_key:
            api_key = cleaned
        elif cleaned.startswith("xsmtpsib-") and not smtp_key:
            smtp_key = cleaned

    # Explicit vars take priority (user may have both keys in correct fields)
    for var in ("BREVO_API_KEY", "BREVO_API", "BREVO_KEY"):
        cleaned = _clean_key(os.getenv(var, ""))
        if cleaned.startswith("xkeysib-"):
            api_key = cleaned
        elif cleaned.startswith("xsmtpsib-") and not smtp_key:
            smtp_key = cleaned

    for var in ("SMTP_PASSWORD", "SMTP_KEY"):
        cleaned = _clean_key(os.getenv(var, ""))
        if cleaned.startswith("xsmtpsib-"):
            smtp_key = cleaned
        elif cleaned.startswith("xkeysib-") and not api_key:
            api_key = cleaned  # pasted API key into SMTP field by mistake

    return api_key, smtp_key


_brevo_api, _brevo_smtp = _scan_env_keys()
BREVO_API_KEY = _brevo_api
SMTP_PASSWORD = _brevo_smtp or (
    os.getenv("SMTP_PASSWORD", "").replace(" ", "")
    or os.getenv("SMTP_KEY", "").replace(" ", "")
)


def brevo_key_hint() -> str:
    """Safe diagnostic for /health — never exposes the full key."""
    if BREVO_API_KEY.startswith("xkeysib-"):
        return "ok"
    raw = _clean_key(os.getenv("BREVO_API_KEY", ""))
    if not raw:
        return "no xkeysib key found in any env var"
    if raw.startswith("xsmtpsib-"):
        return "BREVO_API_KEY still has xsmtpsib — put xkeysib key there OR in SMTP_PASSWORD"
    return f"unexpected prefix ({raw[:10]}...) — need xkeysib-"

# Must be a verified sender in Brevo (Senders & IP → Senders)
SMTP_FROM_EMAIL = os.getenv("SMTP_FROM_EMAIL", "").strip()
DEBUG_MODE = os.getenv("DEBUG_MODE", "true").lower() == "true"
ON_RENDER = bool(os.getenv("RENDER"))

# Comma-separated list of allowed frontend origins for CORS
CORS_ORIGINS = os.getenv(
    "CORS_ORIGINS",
    "http://localhost:5173,http://127.0.0.1:5173,https://hyundai-intelli-drive-frontend.vercel.app"
    # "http://localhost:5174,http://127.0.0.1:5174,"
    # "http://localhost:5175,http://127.0.0.1:5175"
).split(",")

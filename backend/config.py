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
load_dotenv(BASE_DIR / ".env")  # load_dotenv reads KEY=value pairs into os.environ

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
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USER = os.getenv("SMTP_USER") or os.getenv("LOGIN", "")
_smtp_password = (
    os.getenv("SMTP_PASSWORD", "").replace(" ", "")
    or os.getenv("SMTP_KEY", "").replace(" ", "")
)
_brevo_raw = (
    os.getenv("BREVO_API_KEY", "").strip()
    or os.getenv("BREVO_API", "").strip()
)

# xsmtpsib- = SMTP key (local only). xkeysib- = API key (required on Render free).
if _brevo_raw.startswith("xsmtpsib-"):
    if not _smtp_password or _smtp_password.startswith("your-"):
        _smtp_password = _brevo_raw
    BREVO_API_KEY = ""
elif _brevo_raw.startswith("xkeysib-"):
    BREVO_API_KEY = _brevo_raw
else:
    BREVO_API_KEY = _brevo_raw

SMTP_PASSWORD = _smtp_password
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

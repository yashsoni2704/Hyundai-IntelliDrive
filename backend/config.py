"""Application configuration loaded from environment variables."""

import os
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = BASE_DIR.parent
load_dotenv(BASE_DIR / ".env")

# Paths - Always use absolute paths from PROJECT_ROOT
DATA_DIR = PROJECT_ROOT / "data"
EXCEL_PATH = DATA_DIR / "hyundai_faq.xlsx"
CHROMA_PERSIST_DIR = BASE_DIR / "chroma_db"
INGESTION_META_PATH = CHROMA_PERSIST_DIR / "ingestion_meta.json"
DATABASE_URL = f"sqlite:///{BASE_DIR / 'app.db'}"

# Validate critical files exist
if not EXCEL_PATH.exists():
    raise FileNotFoundError(f"Excel file not found: {EXCEL_PATH}\nPlease ensure hyundai_faq.xlsx is in the data/ folder")

# ChromaDB
COLLECTION_NAME = os.getenv("COLLECTION_NAME", "hyundai_faq")

# Embeddings
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "BAAI/bge-m3")

# Similarity: Chroma cosine distance = 1 - cosine_similarity
SIMILARITY_THRESHOLD = float(os.getenv("SIMILARITY_THRESHOLD", "0.55"))

# JWT
JWT_SECRET = os.getenv("JWT_SECRET", "hyundai-dev-secret-change-in-production")
JWT_ALGORITHM = "HS256"
JWT_EXPIRE_MINUTES = int(os.getenv("JWT_EXPIRE_MINUTES", "1440"))

# Email / OTP — configure in backend/.env (never commit real passwords)
SMTP_HOST = os.getenv("SMTP_HOST", "")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USER = os.getenv("SMTP_USER", "")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "").replace(" ", "")
# Optional override for SendGrid/Mailgun etc. Defaults to SMTP_USER (Gmail).
SMTP_FROM_EMAIL = os.getenv("SMTP_FROM_EMAIL") or SMTP_USER
DEBUG_MODE = os.getenv("DEBUG_MODE", "true").lower() == "true"

# API
CORS_ORIGINS = os.getenv(
    "CORS_ORIGINS",
    "http://localhost:5173,http://127.0.0.1:5173,"
    "http://localhost:5174,http://127.0.0.1:5174,"
    "http://localhost:5175,http://127.0.0.1:5175",
).split(",")
